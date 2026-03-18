from dataclasses import dataclass
from typing import List, Any, Callable, Optional, Dict
from abc import ABC


@dataclass
class BaseContext(ABC):
    """Abstract base for all UI interactions."""
    key: str  # Where the result will be stored in the queue


@dataclass
class InputContext(BaseContext):
    prompt: str
    validator: Callable
    default: Any = None
    buffer: str = ""
    error_msg: Optional[str] = None


@dataclass
class PopupContext(BaseContext):
    title: str
    options: List[str]
    index: int = 0


class UIContextQueue:
    def __init__(self, on_complete: Callable[[Dict], None] = None):
        self.queue: List[BaseContext] = []
        self.active: Optional[BaseContext] = None
        self.results: Dict[str, Any] = {}
        self.on_complete = on_complete

    def add(self, context_obj: BaseContext):
        self.queue.append(context_obj)
        if not self.active:
            self.active = self.queue.pop(0)

    def resolve_active(self, value: Any) -> bool:
        """Saves the value to results and advances the queue."""
        if self.active:
            self.results[self.active.key] = value

        if self.queue:
            self.active = self.queue.pop(0)
            return True

        # Terminal state reached
        final_results = self.results.copy()
        self.active = None
        self.results = {}  # Reset for safety

        if self.on_complete:
            self.on_complete(final_results)
        return False

    def clear(self):
        self.queue = []
        self.active = None
        self.results = {}