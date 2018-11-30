import re
from itertools import chain
from typing import Optional, Dict

recipe_pattern = re.compile('([a-zA-Z_]\w*)\s*{([\d\w, ]+)?}\s*->\s*{([\d\w, ]+)?}\s*(?:\*\s*([\d]+(?:\.\d+)?))?\s*(?:/\s*(\d+(?:\.\d+)?))?')
resource_pattern = re.compile('\s*(\d+)\s*([a-zA-Z_]\w*)')


class ParseError(RuntimeError):
    pass


class Recipe:
    def __init__(self, name, inputs=None, outputs=None, efficiency=1.0, duration=1.0):
        self.name = name
        self._inputs = dict(inputs or [])
        self._outputs = dict(outputs or [])
        self._efficiency = efficiency
        self._duration = duration

    @staticmethod
    def from_str(str, mode='real'):
        # initial reading of the string
        m = recipe_pattern.match(str)
        if m is None:
            raise ParseError('Malformed recipe: ' + str)
        name = m[1]
        r_inputs = m[2]
        r_outputs = m[3]

        efficiency = 1.0 if m[4] is None else float(m[4])
        duration = 1.0 if m[5] is None else float(m[5])

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

        return Recipe(name, inputs, outputs, efficiency, duration)

    def produces(self, resource: str) -> bool:
        return resource in self._outputs

    def requires(self, resource: str) -> bool:
        return resource in self._inputs

    def inputs(self):
        return self._inputs.keys()

    def outputs(self):
        return self._outputs.keys()

    def produced(self, resource: str, batches=1.0) -> float:
        return (self._outputs.get(resource) or 0.0) * (self._efficiency / self._duration) * batches

    def consumed(self, resource: str, batches=1.0) -> float:
        return (self._inputs.get(resource) or 0.0) * (self._efficiency / self._duration) * batches

    def batches_required(self, resource: str, quantity: float):
        if resource in self._inputs:
            # how many batches required to consume this much input
            return quantity / (self._inputs[resource] * (self._efficiency / self._duration))
        if resource in self._outputs:
            # how many batches required to produce this much output
            return quantity / (self._outputs[resource] * (self._efficiency / self._duration))
        # we don't produce or consume it, so no batches are required to consume it
        return 0.0

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        def format_components(comps):
            acc = ''
            for i, (c, n) in enumerate(comps.items()):
                if i > 0: acc += ', '
                acc += '{} {}'.format(n, c)
            return acc

        inputs = format_components(self._inputs)
        outputs = format_components(self._outputs)

        s = '{} {{{}}} -> {{{}}}'.format(self.name, inputs, outputs)
        if self._efficiency != 1.0:
            s += ' * {}'.format(self._efficiency)
        if self._duration != 1.0:
            s += ' / {}'.format(self._duration)
        return s


def read_recipe_book(inputstream):
    recipe_book = {}
    resources = set()
    for l in inputstream:
        if l[0:3] == 'END':
            break
        recipe = Recipe.from_str(l)
        recipe_book[recipe.name] = recipe
        for resource in chain(recipe._inputs, recipe._outputs):
            resources.add(resource)

    recipe_names = set(recipe_book.keys())
    if len(recipe_names & resources) > 0:
        raise ParseError("Cannot have duplicated identifiers between recipes and resources.")

    print("Found recipes: {}".format(sorted(recipe_names)))
    print("Found resources: {}".format(sorted(resources)))
    return recipe_book, resources