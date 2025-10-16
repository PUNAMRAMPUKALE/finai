from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class ProductRepository(ABC):
    @abstractmethod
    def insert_many(self, items: List[Dict[str, Any]]) -> int: ...
    @abstractmethod
    def search_by_vector(self, vector: list, limit: int = 12) -> List[Dict[str, Any]]: ...