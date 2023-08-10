from typing import Any

from halftone.halftone_original import Halftone


def make(path: str, **args: Any) -> None:
    h = Halftone(path)
    h.make(**args)
