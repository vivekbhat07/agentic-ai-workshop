"""Retry with exponential backoff + jitter.

delay = base_delay * 2**attempt  (+ random jitter), capped at max_delay
attempt 0 -> 0.5s, 1 -> 1s, 2 -> 2s, 3 -> 4s ...
"""
import functools
import logging
import random
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from reliability.errors import TransientLLMError

P = ParamSpec("P")
R = TypeVar("R")
log = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    retry_on: tuple[type[BaseException], ...] = (TransientLLMError, TimeoutError),
    sleep: Callable[[float], None] = time.sleep,  # injectable -> tests don't actually wait
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except retry_on as exc:
                    if attempt == max_attempts - 1:
                        raise  # out of attempts: surface the real error
                    delay = min(max_delay, base_delay * 2**attempt)
                    delay += random.uniform(0, delay * 0.1)  # jitter
                    log.warning("Attempt %d failed (%s); retrying in %.2fs",
                                attempt + 1, exc, delay)
                    sleep(delay)
            raise AssertionError("unreachable")

        return wrapper

    return decorator
