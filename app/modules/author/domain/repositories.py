from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Author, AuthorIn


class AuthorRepository(ABC):
    @abstractmethod
    async def create(self, author: AuthorIn) -> Author:  # type: ignore[valid-type]
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, author_id: int) -> Optional[Author]:  # type: ignore[valid-type]
        raise NotImplementedError

    @abstractmethod
    async def list_by_name(self, name: str) -> List[Author]:  # type: ignore[valid-type]
        raise NotImplementedError
