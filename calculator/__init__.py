from fractions import Fraction as _Fraction
from typing import Dict, Tuple, Union

FloatCounts = Dict[str, Tuple[float, float]]
FracCounts = Dict[str, Tuple[_Fraction, _Fraction]]

Counts = Union[FloatCounts, FracCounts]

Targets = Union[Dict[str, float], Dict[str, _Fraction]]

# Max denominator for rational values. Should be small enough that rounding errors in config do not cause issues.
# i.e., we want 0.33333 = 1/3
MAX_DENOMINATOR = 1000

def asfrac(x):
    return _Fraction(x).limit_denominator(MAX_DENOMINATOR)

class ParseError(RuntimeError):
    pass
