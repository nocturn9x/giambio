from ._core import AsyncScheduler
from .exceptions import ErrorStack, CancelledError
import itertools


class TaskManager(object):
    """A task manager"""

    def __init__(self, scheduler: AsyncScheduler):
        """Object constructor"""

        self.scheduler = scheduler
        self.tasks = self.scheduler.tasks
        self.asleep = self.scheduler.paused
        self.event_waiting = self.scheduler.event_waiting
        self.values = {}

    async def __aenter__(self):
        """Implements async with self"""

        return self

    async def _cancel_and_raise(self, err):
        """Cancels all tasks and raises an exception"""

        errors = []
        for task in itertools.chain(
            self.tasks.copy(),
            self.asleep.items(),
            self.event_waiting.values(),
        ):
            await task.cancel()
            try:
                await task.join()
            except Exception as fault:
                fault.__cause__ = None  # We clear this to avoid unrelated tracebacks
                errors.append(fault)
        if errors:
            exc = ErrorStack()
            errors.insert(0, err)
            exc.errors = errors
            raise exc
        raise err

    async def __aexit__(self, exc_type, exc_val, traceback):
        """Implements async with self"""

        while True:
            tasks = itertools.chain(
                self.tasks.copy(), self.asleep.items()
            )
            for task in tasks:
                try:
                    self.values[task] = await task.join()
                except Exception as err:
                    await self._cancel_and_raise(err)

    def create_task(self, coro):
        """Creates a task"""

        return self.scheduler.create_task(coro)
