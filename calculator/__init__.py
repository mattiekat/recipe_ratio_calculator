from typing import Dict, Tuple, Union
from fractions import Fraction

FloatCounts = Dict[str, Tuple[float, float]]
FracCounts = Dict[str, Tuple[Fraction, Fraction]]

Counts = Union[FloatCounts, FracCounts]
Calculations = Union[Tuple[FloatCounts, FloatCounts], Tuple[FracCounts, FracCounts]]

Targets = Union[Dict[str, float], Dict[str, Fraction]]

# Max denominator for rational values. Should be small enough that rounding errors in config do not cause issues.
# i.e., we want 0.33333 = 1/3
MAX_DENOMINATOR = 1000

def asfrac(x):
    return Fraction(x).limit_denominator(MAX_DENOMINATOR)

class ParseError(RuntimeError):
    pass
