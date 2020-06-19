import types
from ._traps import join, cancel


class Task:

    """A simple wrapper around a coroutine object"""

    def __init__(self, coroutine: types.coroutine):
        self.coroutine = coroutine
        self.cancelled = False   # True if the task gets cancelled
        self.exc = None
        self.result = None
        self.finished = False

    def run(self, what=None):
        """Simple abstraction layer over the coroutines ``send`` method"""

        return self.coroutine.send(what)

    def throw(self, err: Exception):
        """Simple abstraction layer over the coroutines ``throw`` method"""

        return self.coroutine.throw(err)

    async def join(self):
        """Joins the task"""

        return await join(self)

    async def cancel(self):
        """Cancels the task"""

        await cancel(self)

    def __repr__(self):
        """Implements repr(self)"""

        return f"Task({self.coroutine}, cancelled={self.cancelled}, exc={repr(self.exc)}, result={self.result}, finished={self.finished})"
