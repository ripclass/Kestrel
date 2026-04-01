from dataclasses import dataclass


@dataclass(slots=True)
class Pagination:
    limit: int = 20
    offset: int = 0
