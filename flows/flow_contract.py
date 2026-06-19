from dataclasses import dataclass
from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class FlowRegistration:
    name: str
    description: str
    builder: Callable[[], Callable]


def define_flow(
    *,
    name: str,
    description: str,
    builder: Callable[[], Callable],
) -> FlowRegistration:
    if not name.strip():
        raise ValueError("name is required")
    if not description.strip():
        raise ValueError("description is required")
    return FlowRegistration(name=name, description=description, builder=builder)
