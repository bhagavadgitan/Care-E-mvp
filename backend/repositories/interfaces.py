"""Database-agnostic repository contracts.

Services depend on these interfaces, never on a concrete database. This is the
seam that lets the MongoDB implementation be swapped for a future PostgreSQL
(or external-integration adapter) implementation without touching services.
"""
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    @abstractmethod
    async def create(self, entity: T) -> T: ...

    @abstractmethod
    async def get(self, id: str) -> Optional[T]: ...

    @abstractmethod
    async def list(self, filters: Optional[dict] = None, limit: int = 100) -> List[T]: ...

    @abstractmethod
    async def update(self, id: str, changes: dict) -> Optional[T]: ...

    @abstractmethod
    async def delete(self, id: str) -> bool: ...
