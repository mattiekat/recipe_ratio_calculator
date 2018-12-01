from typing import Dict, Tuple

Counts = Dict[str, Tuple[float, float]]


class ParseError(RuntimeError):
    pass
