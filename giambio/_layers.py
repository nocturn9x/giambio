import types
from ._traps import join, sleep, cancel


class Task:

    """A simple wrapper around a coroutine object"""

    def __init__(self, coroutine: types.coroutine):
        self.coroutine = coroutine
        self.cancelled = False   # True if the task gets cancelled
        self.exc = None
        self.result = None
        self.finished = False

    def run(self):
        """Simple abstraction layer over the coroutines ``send`` method"""

        return self.coroutine.send(None)

    async def join(self):
        """Joins the task"""

        return await join(self)

    async def cancel(self):
        """Cancels the task"""

        await cancel(self)

    def result(self):
        if self.exc:
            raise self.exc
        return self.result

    def __repr__(self):
        """Implements repr(self)"""

        return f"Task({self.coroutine}, cancelled={self.cancelled}, exc={repr(self.exc)}, result={self.result}, finished={self.finished})"
