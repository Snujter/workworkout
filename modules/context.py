import time
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
    cursor_y: int = 0
    cursor_x: int = 0


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


class TimerContext:
    def __init__(self, interval_seconds):
        self.interval_seconds: int = interval_seconds
        self.last_alert_time = time.time()
        self.is_paused: bool = False
        self.elapsed_at_pause: int = 0

    def get_elapsed(self):
        if self.is_paused:
            return self.elapsed_at_pause
        return time.time() - self.last_alert_time

    def get_time_left(self):
        elapsed = self.get_elapsed()
        return max(0, int(self.interval_seconds - elapsed))

    def check_trigger(self, on_expire: Callable[[], None]=None):
        if self.is_paused:
            return False

        if self.get_elapsed() >= self.interval_seconds:
            # Handle any callbacks on expiration
            if callable(on_expire):
                on_expire()

            # Reset the internal anchor
            self.reset()
            return True
        return False

    def toggle_pause(self):
        if not self.is_paused:
            self.elapsed_at_pause = time.time() - self.last_alert_time
            self.is_paused = True
        else:
            # Shift the start time forward by the frozen duration
            self.last_alert_time = time.time() - self.elapsed_at_pause
            self.is_paused = False

    def reset(self):
        """Resets the anchor to the current time."""
        self.last_alert_time = time.time()
        self.elapsed_at_pause = 0