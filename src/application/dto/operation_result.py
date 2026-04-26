from dataclasses import dataclass
from typing import Generic, Optional, TypeVar


T = TypeVar("T")


@dataclass
class OperationResult(Generic[T]):
    """Represent the outcome of an application use case."""

    ok: bool
    data: Optional[T] = None
    error: Optional[str] = None
