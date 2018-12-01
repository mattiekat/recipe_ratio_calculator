from calculator.recipe import Crafter, Recipe
from itertools import chain
from typing import Dict, Set, Optional
from calculator import ParseError, Counts
import re
from typing import Tuple

default_pattern = re.compile('([a-zA-Z_]\w*)\s+([a-zA-Z_]+)\s*$')


class RecipeBook:
    def __init__(self):
        self._recipes: Dict[str, Recipe] = {}
        self._resources: Set[str] = set()
        self._defaults: Dict[str, Optional[Recipe]] = {}
        self._crafters: Dict[str, Crafter] = {}

    def add_recipes_from_stream(self, inputstream):
        """
        Read multiple recipes and add them to this book. This will continue reading until "END" is read.

        If any new recipes have the same name as an existing recipe, the old one will be replaced.

        :param inputstream: A file, stdin, or other iterable object which yields a single line at a time.
        """

        for l in inputstream:
            if l[0:3] == 'END':
                break
            recipe = Recipe.from_str(l)

            if recipe.name in self._resources:
                raise ParseError("Cannot have duplicated identifiers between recipes and resources.")
            for resource in chain(recipe.inputs(), recipe.outputs()):
                if resource in self._recipes:
                    raise ParseError("Cannot have duplicated identifiers between recipes and resources.")

            self._recipes[recipe.name] = recipe
            for resource in chain(recipe.inputs(), recipe.outputs()):
                self._resources.add(resource)

    def set_defaults_from_stream(self, inputstream):
        """
        Read multiple default recipe choices for given resources. This will continue reading until "END" is read.

        New defaults will override existing ones.

        :param inputstream: A file, stdin, or other iterable object which yields a single line at a time.
        """
        for l in inputstream:
            if l[0:3] == 'END':
                break
            m = default_pattern.match(l)
            if m is None:
                raise ParseError("Invalid default definition: " + l)

            resource, recipe = m[1], m[2]
            if not self.is_resource(resource):
                raise ParseError("No resource '{}' found".format(resource))
            if not self.is_recipe(recipe):
                raise ParseError("No recipe '{}' found".format(recipe))
            recipe = self[recipe]
            if not recipe.produces(resource):
                raise ParseError("The recipe '{}' does not produce the resource '{}'".format(recipe, resource))

            self._defaults[resource] = recipe

    def set_crafters_from_stream(self, inputstream):
        """
        Read multiple default crafter choices for given resources. This will continue reading until "END" is read.
        New values will override existing ones.

        :param inputstream: A file, stdin, or other iterable object which yields a single line at a time.
        """
        for l in inputstream:
            if l[0:3] == 'END':
                break

            crafter = Crafter.from_str(l)

            for r in crafter.recipes:
                if not self.is_recipe(r):
                    raise ParseError("No recipe '{}' found".format(r))

            # make them references to the same string to save memory and make comparisons easier
            crafter.recipes = set(map(lambda r: self[r].name, crafter.recipes))

            self._crafters[crafter.name] = crafter
            for recipe in map(self.__getitem__, crafter.recipes):
                recipe.crafter = crafter

    def calculate(self, targets: Dict[str, float]) -> Tuple[Counts, Counts]:
        """
        Calculate the number of resources and batches of each recipe are needed to meet all the user, production targets.

        Note: Production targets for resources define how many of the resource must be "left over" (i.e. not consumed by
        other recipes) while production targets for recipes define the minimum number of batches which must be run.

        :param targets: Production targets specified by the user.
        :return: The total recipe batches and resource counts.
        """

        # the total quantity of an ingredient/resource
        #       first part is the "demand", i.e. how much is required
        #       second part is the "supply", i.e. how much will be produced (may be greater than demand if it's a byproduct)
        resource_counts = {}

        # how many batches are we producing of each recipe
        recipe_batches = {}

        # set the demand for each target as the required quantities
        for target, required in targets.items():
            if self.is_recipe(target):
                recipe_batches[target] = (required, 0.0)
            elif self.is_resource(target):
                # find it's recipe and add that
                recipe = self.get_recipe_for(target)
                if recipe is None:
                    # raw resource, not sure why it was requested, but give them what they want
                    resource_counts[target] = (required, required)
                else:
                    resource_counts[target] = (required, 0.0)
                    recipe_batches[recipe.name] = (0.0, 0.0)
            else:
                raise RuntimeError("Unrecognized identifier: " + target)

        while self._propagate(recipe_batches, resource_counts):
            # multiple iterations are required when recipes produces useful byproducts
            pass

        return recipe_batches, resource_counts

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

        # there is more than one recipe, so prompt the user
        print("Please select a recipe for '{}'".format(resource))
        for i, o in enumerate(available):
            print("{}: {}".format(i + 1, repr(o)))
        choice = int(input('=> '))
        choice = available[choice - 1]

        self._defaults[resource] = choice
        return choice

    def get_crafter_for(self, recipe: str) -> Optional[Crafter]:
        """
        Find what crafter is being used to produce this recipe.

        :param recipe: Recipe to find the crafter for.
        :return: Chosen recipe to produce the resource or None if it is a raw resource that has no recipe.
        """
        return self[recipe].crafter

    def is_recipe(self, identifier):
        return identifier in self._recipes

    def is_resource(self, identifier):
        return identifier in self._resources

    def is_raw_resource(self, resource):
        return self.get_recipe_for(resource) is None

    def recipes(self):
        return self._recipes.keys()

    def resources(self):
        return iter(self._resources)

    def crafters_defined(self):
        return len(self._crafters) > 0

    def _propagate(self, recipe_batches: Counts, resource_counts: Counts) -> bool:
        """
        Construct and propagate the implications of what recipe requirements we know to determine the total requirements of
        production by updating the batches and the resulting quantities of produced resources. This needs to be called
        multiple times for some problems to find an optimal solution.

        :param book: Book of all available recipes.
        :param recipe_batches: Counts for each of the recipe nodes.
        :param resource_counts: Counts for each of the resource nodes.
        :return: Whether any changes were made to the graph.
        """

        pending_changes: Set[str] = set(recipe_batches.keys())
        changes_made = False
        while pending_changes:
            # 1) choose a recipe node which needs to be updated
            recipe = self[pending_changes.pop()]

            # 2) find the total number of batches needed to produce the demanded output (for which it is the recipe of)
            base_batches = recipe_batches.get(recipe.name) or (0.0, 0.0)
            # If not reducing: the user may request a minimum number of batches (will be >= 0)
            # If reducing: max number of batches we can remove (will be <= 0) while preserving the user requested min
            batches = max(0.0, base_batches[0] - base_batches[1])

            for resource in recipe.outputs():
                demand, supply = resource_counts.get(resource) or (0.0, 0.0)

                if batches < 0.0:
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

            # the new number of batches must satisfy the minimum specified by the user
            assert base_batches[1] + batches >= base_batches[0]
            if batches == 0:
                # nothing changes
                continue
            changes_made = True

            # update the current number of batches to the new number we have deemed appropriate
            recipe_batches[recipe.name] = (base_batches[0], base_batches[1] + batches)

            # 3) update the input resources to reflect the new demand
            for resource in recipe.inputs():
                counts = resource_counts.get(resource) or (0.0, 0.0)
                counts = (counts[0] + recipe.consumed(resource, batches), counts[1])  # increase/decrease demand

                # mark it's producing recipe as needing to be updated (if not raw)
                r2 = self.get_recipe_for(resource)
                if r2 is None:
                    # it's a raw resource, so supply = demand
                    counts = (counts[0], counts[0])
                else:
                    pending_changes.add(r2.name)
                resource_counts[resource] = counts

            # 4) update the output resources to reflect the new supply
            for resource in recipe.outputs():
                counts = resource_counts.get(resource) or (0.0, 0.0)
                counts = (counts[0], counts[1] + recipe.produced(resource, batches))  # increase/decrease supply
                resource_counts[resource] = counts

        return changes_made
