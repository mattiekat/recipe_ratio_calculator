import re
from fractions import Fraction
from typing import Dict, List, Union

from calculator import ParseError, asfrac

recipe_pattern = re.compile('([a-zA-Z_]\w*)\s*{([\d\w, ]+)?}\s*->\s*{([\d\w, ]+)?}\s*(?:/\s*(\d+(?:\.\d+)?))?\s*$')
resource_pattern = re.compile('\s*(\d+)\s+([a-zA-Z_]\w*)')


class Crafter:
    def __init__(self, name: str, efficiency: float):
        self.name = name
        self.efficiency = efficiency

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return self.name


class Recipe:
    def __init__(self, name, inputs=None, outputs=None, duration=1.0, crafters=None):
        """
        Create a new recipe.
        :param name: Recipe identifier name.
        :param inputs: Optional list of inputs which can be converted to a Dict[str, float] with the key the resource
            name, and the value the amount required for the recipe.
        :param outputs: Optional list of outputs which can be converted to a Dict[str, float] with the key the resource
            name, and the value the amount produced by the recipe.
        :param duration: The amount of time a standard system would take to make this recipe.
        :param crafters: List of crafters which can make this recipe.
        """
        self.name = name
        self._inputs: Dict[str, float] = dict(inputs or [])
        self._outputs: Dict[str, float] = dict(outputs or [])
        self._duration: float = duration
        self.crafters: List[Crafter] = crafters

    @staticmethod
    def from_obj(name, obj: Dict, aval_crafters: Dict[str, Crafter]):
        """
        Parse an object representation of a recipe. Mostly to read from YAML or JSON.
        :param name: Name of the new recipe.
        :param obj: See recipe schema in readme.
        :param aval_crafters: Available crafters which can be specified.
        :return: A new recipe object.
        """
        inputs = {}
        outputs = {}
        duration = 1.0
        crafters = []

        if 'inputs' in obj:
            for resource, count in obj['inputs'].items():
                inputs[resource] = float(count)
        if 'outputs' in obj:
            for resource, count in obj['outputs'].items():
                outputs[resource] = float(count)

        if len(inputs) and len(outputs) == 0:
            raise ParseError("Recipe {} does not have inputs or outputs!".format(name))
        if len(set(inputs.keys()) & set(outputs.keys())) > 0:
            raise ParseError("Recipe {} has an output which is also an input!".format(name))

        if 'duration' in obj:
            duration = float(obj['duration'])

        if 'crafters' in obj:
            if type(obj['crafters']) == str:
                obj['crafters'] = [obj['crafters']]
            for c in obj['crafters']:
                if c not in aval_crafters:
                    raise ParseError('Crafter {} not defined.'.format(c))
                crafters.append(aval_crafters[c])

        return Recipe(name, inputs, outputs, duration, crafters)

    def efficiency(self):
        return 1.0 if len(self.crafters) == 0 else self.crafters[0].efficiency

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

    def produced(self, resource: str, batches: Union[float, Fraction]=1.0) -> Union[float, Fraction]:
        """
        Calculate how much of a given resource would be produced given a certain number of batches are run.
        """
        o = self._outputs.get(resource) or 0.0
        e = self.efficiency()
        d = self._duration

        if type(batches) == Fraction:
            o = asfrac(o)
            e = asfrac(e)
            d = asfrac(d)

        return o * (e / d) * batches

    def consumed(self, resource: str, batches: Union[float, Fraction]=1.0) -> Union[float, Fraction]:
        """
        Calculate how much of a given resource would be consumed given a certain number of batches are run.
        """
        i = self._inputs.get(resource) or 0.0
        e = self.efficiency()
        d = self._duration

        if type(batches) == Fraction:
            i = asfrac(i)
            e = asfrac(e)
            d = asfrac(d)

        return i * (e / d) * batches

    def batches_required(self, resource: str, quantity: Union[float, Fraction]) -> Union[float, Fraction]:
        """
        Calculate how many batches would be required to produce a certain quantity of the specified resource if it is an
        input, otherwise how many batches would be required to consume that quantity of the specified resource.
        """
        use_fractions = type(quantity) == Fraction
        e = self.efficiency()
        d = self._duration
        z = 0.0

        if use_fractions:
            e = asfrac(e)
            d = asfrac(d)
            z = asfrac(z)

        if resource in self._inputs:
            # how many batches required to consume this much input
            i = self._inputs[resource]
            if use_fractions: i = asfrac(i)
            return quantity / (i * (e / d))
        if resource in self._outputs:
            # how many batches required to produce this much output
            o = self._outputs[resource]
            if use_fractions: o = asfrac(o)
            return quantity / (o * (e / d))

        # we don't produce or consume it, so no batches are required to consume it
        return z

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
