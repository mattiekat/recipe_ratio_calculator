import re
from itertools import chain
from typing import Dict, Set, Optional

recipe_pattern = re.compile('([a-zA-Z_]\w*)\s*{([\d\w, ]+)?}\s*->\s*{([\d\w, ]+)?}\s*(?:/\s*(\d+(?:\.\d+)?))?\s*$')
resource_pattern = re.compile('\s*(\d+)\s+([a-zA-Z_]\w*)')
default_pattern = re.compile('([a-zA-Z_]\w*)\s+([a-zA-Z_]+)\s*$')
crafter_pattern = re.compile('([a-zA-Z_]\w*)\s+(\d+(?:\.\d+)?)\s+(.*)$')


class ParseError(RuntimeError):
    pass


class Recipe:
    def __init__(self, name, inputs=None, outputs=None, duration=1.0, crafter=None):
        """
        Create a new recipe.
        :param name: Recipe identifier name.
        :param inputs: Optional list of inputs which can be converted to a Dict[str, float] with the key the resource
            name, and the value the amount required for the recipe.
        :param outputs: Optional list of outputs which can be converted to a Dict[str, float] with the key the resource
            name, and the value the amount produced by the recipe.
        :param efficiency: The rate at which a machine making this recipe works.
        :param duration: The amount of time a standard system would take to make this recipe.
        """
        self.name = name
        self._inputs = dict(inputs or [])
        self._outputs = dict(outputs or [])
        self._duration = duration
        self.crafter = crafter

    @staticmethod
    def from_str(str, mode='real'):
        """
        Parses a string version of a recipe in the form `{1 input1, 3 input2} -> {2 output} * efficiency/duration`.
        :param str: The string to parse
        :param mode: Does nothing at this time.
        :return: The converted recipe.
        """
        # initial reading of the string
        m = recipe_pattern.match(str)
        if m is None:
            raise ParseError('Malformed recipe: ' + str)
        name = m[1]
        r_inputs = m[2]
        r_outputs = m[3]

        duration = 1.0 if m[4] is None else float(m[4])

        # parse the raw inputs and outputs strings
        inputs = {}
        outputs = {}

        if r_inputs is not None:
            for input in r_inputs.split(','):
                m = resource_pattern.match(input)
                if m is None:
                    raise ParseError('Malformed inputs: ' + r_inputs)
                inputs[m[2]] = int(m[1])
        if r_outputs is not None:
            for output in r_outputs.split(','):
                m = resource_pattern.match(output)
                if m is None:
                    raise ParseError('Malformed outputs: ' + r_outputs)
                outputs[m[2]] = int(m[1])
        if r_outputs is None and r_inputs is None:
            raise ParseError('Recipe must have at least one input or output: ' + str)

        return Recipe(name, inputs, outputs, duration)

    def efficiency(self):
        return 1.0 if self.crafter is None else self.crafter.efficiency

    def produces(self, resource: str) -> bool:
        """
        Check if this recipe produces the specified resource.
        """
        return resource in self._outputs

    def requires(self, resource: str) -> bool:
        """
        Check if this recipe requires the specified resource.
        """
        return resource in self._inputs

    def inputs(self):
        """
        Get an iterator over the input resource names.
        """
        return self._inputs.keys()

    def outputs(self):
        """
        Get an iterator over the output resource names.
        """
        return self._outputs.keys()

    def produced(self, resource: str, batches=1.0) -> float:
        """
        Calculate how much of a given resource would be produced given a certain number of batches are run.
        """
        return (self._outputs.get(resource) or 0.0) * (self.efficiency() / self._duration) * batches

    def consumed(self, resource: str, batches=1.0) -> float:
        """
        Calculate how much of a given resource would be consumed given a certain number of batches are run.
        """
        return (self._inputs.get(resource) or 0.0) * (self.efficiency() / self._duration) * batches

    def batches_required(self, resource: str, quantity: float):
        """
        Calculate how many batches would be required to produce a certain quantity of the specified resource if it is an
        input, otherwise how many batches would be required to consume that quantity of the specified resource.
        """
        if resource in self._inputs:
            # how many batches required to consume this much input
            return quantity / (self._inputs[resource] * (self.efficiency() / self._duration))
        if resource in self._outputs:
            # how many batches required to produce this much output
            return quantity / (self._outputs[resource] * (self.efficiency() / self._duration))
        # we don't produce or consume it, so no batches are required to consume it
        return 0.0

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        """
        Simply the identifier of the recipe.
        """
        return self.name

    def __repr__(self):
        """
        Full string description of the recipe and its inputs, outputs, efficency, and duration. This is the same format
        as `from_str` expects.
        """
        def format_components(comps):
            acc = ''
            for i, (c, n) in enumerate(comps.items()):
                if i > 0: acc += ', '
                acc += '{} {}'.format(n, c)
            return acc

        inputs = format_components(self._inputs)
        outputs = format_components(self._outputs)

        s = '{} {{{}}} -> {{{}}}'.format(self.name, inputs, outputs)
        if self._duration != 1.0:
            s += ' / {}'.format(self._duration)
        return s


class Crafter:
    def __init__(self, name: str, recipes: Set[str], efficiency: float):
        self.name = name
        self.efficiency = efficiency
        self.recipes = set(recipes)

    @staticmethod
    def from_str(str):
        m = crafter_pattern.match(str)
        if m is None:
            raise ParseError("Invalid crafter description: " + str)
        recipes = set(l.strip() for l in m[3].split(','))
        recipes.discard('')
        return Crafter(m[1], recipes, float(m[2]))

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return self.name


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
