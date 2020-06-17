from ._core import AsyncScheduler
from types import coroutine


def run(coro: coroutine):
    """Shorthand for giambio.AsyncScheduler().start(coro)"""

    ...  # How to do it? (Share objects between coroutines etc)
