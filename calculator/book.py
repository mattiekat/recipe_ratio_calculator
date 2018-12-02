import sys
from fractions import Fraction
from math import ceil, floor
from typing import Dict, Set, Optional

from tabulate import tabulate

from calculator import ParseError, Targets, asfrac
from calculator.recipe import Recipe, Crafter


class Calculations:
    """
    The solved graph representing the total number of batches and resource costs.
    """

    def __init__(self, book, targets, recipes=None, resources=None):
        """
        :param book: The recipe book this solution is based on.
        :param recipes: Number of batches each recipe is run.
        :param resources: Quantity of each resource required.
        """
        self.book = book
        self.targets = targets

        # the total quantity of an ingredient/resource
        #       first part is the "demand", i.e. how much is required
        #       second part is the "supply", i.e. how much will be produced (may be greater than demand if it's a byproduct)
        self.recipes = recipes or {}

        # how many batches are we producing of each recipe
        self.resources = resources or {}

    def tabulate_recipes(self, **kwargs) -> str:
        """
        Create an ascii table of the required recipe batches to accomplish the targets.
        :param kwargs: Additional arguments to pass to tabulate.
        :return: String of the ascii table.
        """
        if self.book.crafters_defined():
            rows = sorted(map(lambda kv: [
                self.book.get_crafter_for(kv[0]) or 'Default',
                kv[0], kv[1][1], kv[1][0]
            ], self.recipes.items()))
            return tabulate(rows, headers=['Crafter', 'Recipe', 'Required', 'Requested'], **kwargs)
        else:
            rows = sorted(map(lambda kv: [
                kv[0], kv[1][1], kv[1][0]
            ], self.recipes.items()))
            return tabulate(rows, headers=['Recipe', 'Required', 'Requested'], **kwargs)

    def tabulate_resources(self, **kwargs) -> str:
        """
        Create an ascii table of the quantities of required resources to accomplish the targets.
        :param kwargs: Additional arguments to pass to tabulate.
        :return: String of the ascii table.
        """
        rows = sorted(map(lambda kv: [
            kv[0],
            kv[1][0] - (self.targets.get(kv[0]) or 0.0),
            self.targets.get(kv[0]) or 0.0,
            kv[1][1] - kv[1][0]
        ], self.resources.items()))
        return tabulate(rows, headers=['Resource', 'UsednProd', 'Requested', 'Excess'], **kwargs)

    def graph_representation(self):
        """
        Construct a dot graph representation of these results.
        :return: The dot graph
        """
        from pydot import Dot, Edge, Node

        g = Dot()

        for resource, quantity in self.resources.items():
            g.add_node(Node('i_' + resource, label='{:.3} {}'.format(quantity[1], resource), style='dashed'))
        for recipe, batches in self.recipes.items():
            g.add_node(Node('r_' + recipe, label='{:.3} {}'.format(batches[1], recipe), shape='box'))

            r: Recipe = self.book[recipe]
            for output in r.outputs():
                weight = r.produced(output, batches[1])
                g.add_edge(Edge('r_' + recipe, 'i_' + output, label='{:.3}'.format(weight), weight=weight))
            for input in r.inputs():
                weight = r.consumed(input, batches[1])
                g.add_edge(Edge('i_' + input, 'r_' + recipe, label='{:.3}'.format(weight), weight=weight))

        return g

    def write_graph(self, path='out', fmt='png'):
        g = self.graph_representation()
        g.write('{}.{}'.format(path, fmt), format=fmt)


class RecipeBook:
    def __init__(self):
        self._recipes: Dict[str, Recipe] = {}
        self._resources: Set[str] = set()
        self._defaults: Dict[str, Optional[Recipe]] = {}
        self._crafters: Dict[str, Crafter] = {}

    @staticmethod
    def from_obj(book: Dict, defaults: Optional[Dict]=None):
        """
        Parse a recipe book object. Mostly to read from YAML or JSON.
        :param book: See the recipe book schema in the readme.
        :param defaults: See the defaults schema in the readme. (This is to override defaults in the book object.)
        :return: a new RecipeBook
        """
        self = RecipeBook()

        if 'crafters' in book:
            for name, speed in book['crafters'].items():
                self._crafters[name] = Crafter(name, float(speed))

        # if a recipes section is missing, assume the whole obj is that section
        recipes = book.get('recipes') or book
        for name, obj in recipes.items():
            r = Recipe.from_obj(name, obj, self._crafters)
            self._resources.update(r.inputs())
            self._resources.update(r.outputs())
            self._recipes[name] = r

        if 'defaults' in book:
            for resource, recipe in book['defaults'].items():
                self.set_default_recipe(resource, recipe)

        if defaults:
            self.set_defaults_from_obj(defaults)

        return self

    def set_defaults_from_obj(self, obj):
        """
        Override current recipe defaults and crafters which will be used.
        :param obj: See the defaults schema in the readme.
        """
        recipes = {}
        crafters = {}

        if 'recipes' in obj:
            recipes = obj['recipes']
            if 'crafters' in obj:
                crafters = obj['crafters']
        elif 'crafters' in obj:
            crafters = obj['crafters']
        else:
            recipes = obj

        for resource, recipe in recipes.items():
            self.set_default_recipe(resource, str(recipe))
        for recipe, crafter in crafters.items():
            self.set_default_crafter(recipe, str(crafter))

    def calculate(self, targets: Targets, use_fractions=False, round_batches=False, round_resources=False, max_iterations=10) -> Calculations:
        """
        Calculate the number of resources and batches of each recipe are needed to meet all the user, production targets.
        If targets is of fractions, then all calculations will be done with fractions.

        Note: Production targets for resources define how many of the resource must be "left over" (i.e. not consumed by
        other recipes) while production targets for recipes define the minimum number of batches which must be run.

        Note: If a target is both listed as a recipe and a resource, the resource is assumed.

        :param targets: Production targets specified by the user.
        :param round_batches: If true, it will round up the number of batches required (and propagate the consequences).
        :param round_resources: If true, it will round up the number of resources required (and propagate the consequences).
        :param max_iterations: Should only take 2-3 total iterations if rounding is disabled, may want a higher value in some cases.
        :return: The total recipe batches and resource counts.
        """
        z, zt = RecipeBook.zero(use_fractions)
        calcs = Calculations(self, targets)

        # set the demand for each target as the required quantities
        for target, required in targets.items():
            if use_fractions:
                required = asfrac(required)
            if self.is_resource(target):
                # find it's recipe and add that
                recipe = self.get_recipe_for(target)
                if recipe is None:
                    # raw resource, not sure why it was requested, but give them what they want
                    calcs.resources[target] = (required, required)
                else:
                    calcs.resources[target] = (required, z())
                    calcs.recipes[recipe.name] = zt()
            elif self.is_recipe(target):
                calcs.recipes[target] = (required, z())
            else:
                raise RuntimeError("Unrecognized identifier: " + target)

        changed = False
        for _ in range(max_iterations):
            # multiple iterations are required when recipes produces useful byproducts
            changed = self._propagate(calcs, round_batches, round_resources, use_fractions)
            if not changed:
                break
        if changed:
            print("May not have found an optimal solution, consider increasing the maximum iterations.", file=sys.stderr)

        return calcs

    def get(self, name):
        return self._recipes.get(name)

    def __getitem__(self, name):
        return self._recipes[name]

    def get_recipe_for(self, resource: str) -> Optional[Recipe]:
        """
        Find a recipe to produce a resource. If multiple recipes are present, prompt the user to decide which one
        should be used for that resource.

        :param resource: Resource to find and pick a recipe for.
        :return: Chosen recipe to produce the resource or None if it is a raw resource that has no recipe.
        """
        if resource in self._defaults:
            return self._defaults[resource]

        available = list(filter(None, map(
            lambda recipe: recipe if recipe.produces(resource) else None,
            self._recipes.values()
        )))

        if len(available) == 1:
            # there is exactly one recipe, so use it
            return available[0]
        if len(available) == 0:
            # there is no recipe, it is a raw resource
            return None

        # there is more than one recipe, so just choose the first and warn the user
        print("Multiple recipes ({}) for {}. Choosing: {}.".format(available, resource, available[0]))
        return available[0]

    def get_crafter_for(self, recipe: str) -> Optional[Crafter]:
        """
        Find what crafter is being used to produce this recipe.

        :param recipe: Recipe to find the crafter for.
        :return: Chosen recipe to produce the resource or None if it is a raw resource that has no recipe.
        """
        crafters = self[recipe].crafters
        return None if crafters is None else crafters[0]

    def is_recipe(self, identifier):
        return identifier in self._recipes

    def is_resource(self, identifier):
        return identifier in self._resources

    def is_crafter(self, identifier):
        return identifier in self._crafters

    def is_raw_resource(self, resource):
        return self.get_recipe_for(resource) is None

    def recipes(self):
        return self._recipes.keys()

    def resources(self):
        return iter(self._resources)

    def crafters_defined(self):
        return len(self._crafters) > 0

    def set_default_recipe(self, resource: str, recipe: str):
        if not self.is_resource(resource):
            raise ParseError("Resource '{}' not defined.".format(resource))
        if not self.is_recipe(recipe):
            raise ParseError("Recipe '{}' not defined.".format(recipe))
        self._defaults[resource] = self[recipe]

    def set_default_crafter(self, recipe: str, crafter: str):
        if not self.is_recipe(recipe):
            raise ParseError("Recipe '{}' is not defined.".format(recipe))
        if not self.is_crafter(crafter):
            raise ParseError("Crafter '{}' is not defined.".format(crafter))
        crafter = self._crafters[crafter]
        rcrafters = self._recipes[recipe].crafters  # the recipe's crafter list
        try:
            index = rcrafters.index(crafter)
            # swap the one we want with the front of the list
            rcrafters[0], rcrafters[index] = rcrafters[index], rcrafters[0]
        except ValueError:
            raise ParseError("Crafter '{}' if not able to craft '{}'.".format(crafter.name, recipe))

    def _propagate(self, calcs: Calculations, round_batches: bool, round_resources: bool, use_fractions=False) -> bool:
        """
        Construct and propagate the implications of what recipe requirements we know to determine the total requirements of
        production by updating the batches and the resulting quantities of produced resources. This needs to be called
        multiple times for some problems to find an optimal solution.

        :param book: Book of all available recipes.
        :param calcs: Stored calculation information to solve this problem.
        :param use_fractions: Whether fractions should be used for computation
        :param round_batches: If true, it will round up the number of batches required (and propagate the consequences).
        :param round_resources: If true, it will round up the number of resources required (and propagate the consequences).
        :return: Whether any changes were made to the graph.
        """
        pending_changes: Set[str] = set(calcs.recipes.keys())
        changes_made = False
        z, zt = RecipeBook.zero(use_fractions)

        while pending_changes:
            # 1) choose a recipe node which needs to be updated
            recipe = self[pending_changes.pop()]

            # 2) find the total number of batches needed to produce the demanded output (for which it is the recipe of)
            base_batches = calcs.recipes.get(recipe.name) or zt()
            # If not reducing: the user may request a minimum number of batches (will be >= 0)
            # If reducing: max number of batches we can remove (will be <= 0) while preserving the user requested min
            batches = max(z(), base_batches[0] - base_batches[1])

            for resource in recipe.outputs():
                demand, supply = calcs.resources.get(resource) or zt()

                if batches < 0:
                    # Cannot reduce the number of batches below the demanded amount even if this is not designated recipe
                    pass
                elif demand <= supply or self.get_recipe_for(resource) != recipe:
                    # if it is already supplied, don't bother
                    # if this is not the primary recipe for the resource, do not modify the number of batches based on it
                    continue

                # If not reducing: use the difference; other things may add to the resource so we cannot start from scratch
                # If reducing: number we can remove is the minimum magnitude that can be removed from all resources
                #   (which becomes the maximum since the values are negative)
                batches = max(batches, recipe.batches_required(resource, demand - supply))

            if round_batches:
                batches = ceil(batches)

            # the new number of batches must satisfy the minimum specified by the user
            assert base_batches[1] + batches >= base_batches[0]
            if batches == 0:
                # nothing changes
                continue
            changes_made = True

            # update the current number of batches to the new number we have deemed appropriate
            calcs.recipes[recipe.name] = (base_batches[0], base_batches[1] + batches)

            # 3) update the input resources to reflect the new demand
            for resource in recipe.inputs():
                counts = calcs.resources.get(resource) or zt()
                consumed = counts[0] + recipe.consumed(resource, batches)
                if round_resources:
                    consumed = ceil(consumed)
                counts = (consumed, counts[1])  # increase/decrease demand

                # mark it's producing recipe as needing to be updated (if not raw)
                r2 = self.get_recipe_for(resource)
                if r2 is None:
                    # it's a raw resource, so supply = demand
                    counts = (counts[0], counts[0])
                else:
                    pending_changes.add(r2.name)
                calcs.resources[resource] = counts

            # 4) update the output resources to reflect the new supply
            for resource in recipe.outputs():
                counts = calcs.resources.get(resource) or zt()
                produced = counts[1] + recipe.produced(resource, batches)
                if round_resources:
                    produced = floor(produced)
                counts = (counts[0], produced)  # increase/decrease supply
                calcs.resources[resource] = counts

        return changes_made

    @staticmethod
    def zero(use_fractions):
        if use_fractions:
            return lambda: Fraction(0), lambda: (Fraction(0), Fraction(0))
        else:
            return lambda: 0.0, lambda: (0.0, 0.0)
