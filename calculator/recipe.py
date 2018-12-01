import re
from typing import Set
from calculator import ParseError

recipe_pattern = re.compile('([a-zA-Z_]\w*)\s*{([\d\w, ]+)?}\s*->\s*{([\d\w, ]+)?}\s*(?:/\s*(\d+(?:\.\d+)?))?\s*$')
resource_pattern = re.compile('\s*(\d+)\s+([a-zA-Z_]\w*)')
crafter_pattern = re.compile('([a-zA-Z_]\w*)\s+(\d+(?:\.\d+)?)\s+(.*)$')


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
