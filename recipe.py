from collections import namedtuple
import re

Component = namedtuple('Component', ['name', 'quantity'])
recipe_pattern = re.compile('([a-zA-Z_]\w*)\s*{([\d\w, ]+)?}\s*->\s*{([\d\w, ]+)?}\s*(?:\*\s*([\d]+(?:\.\d+)?))?\s*(?:/\s*(\d+(?:\.\d+)?))?')
component_pattern = re.compile('(\d+)\s*([a-zA-Z_]\w*)')


class ParseError(RuntimeError):
    pass


class Recipe:
    def __init__(self, name, inputs=None, outputs=None, efficiency=1.0, duration=1.0):
        self.name = name
        self.inputs = set(inputs or [])
        self.outputs = set(outputs or [])
        self.efficiency = efficiency
        self.duration = duration

    @staticmethod
    def from_str(str, mode='real'):
        # initial reading of the string
        m = recipe_pattern.match(str)
        if m is None:
            raise ParseError('Malformed recipe: ' + str)
        name = m[1]
        r_inputs = m[2] or ''
        r_outputs = m[3] or ''

        efficiency = float(m[4])
        duration = float(m[5])

        # parse the raw inputs and outputs strings
        inputs = set()
        outputs = set()
        for input in r_inputs.split(','):
            m = component_pattern.match(input)
            if m is None:
                raise ParseError('Malformed inputs: ' + r_inputs)
            inputs.add(Component(name=m[2], quantity=m[1]))

        for output in r_outputs.split(','):
            m = component_pattern.match(output)
            if m is None:
                raise ParseError('Malformed outputs: ' + r_inputs)
            outputs.add(Component(name=m[2], quantity=m[1]))

        return Recipe(name, inputs, outputs, efficiency, duration)
