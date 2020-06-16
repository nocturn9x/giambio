import types
from ._traps import join, sleep, cancel
from .exceptions import CancelledError

class Task:

    """A simple wrapper around a coroutine object"""

    def __init__(self, coroutine: types.coroutine):
        self.coroutine = coroutine
        self.joined = False   # True if the task is joined
        self.cancelled = False   # True if the task gets cancelled

    def run(self):
        """Simple abstraction layer over the coroutines ``send`` method"""

        return self.coroutine.send(None)

    async def join(self):
        """Joins the task"""

        return await join(self)

    async def cancel(self):
        """Cancels the task"""

        await cancel(self)

