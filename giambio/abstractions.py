import types
from .traps import join, sleep, want_read, want_write, cancel
from .exceptions import CancelledError

class Result:
    """A wrapper for results of coroutines"""

    def __init__(self, val=None, exc: Exception = None):
        self.val = val
        self.exc = exc

    def __repr__(self):
        return f"giambio.core.Result({self.val}, {self.exc})"


class Task:

    """A simple wrapper around a coroutine object"""

    def __init__(self, coroutine: types.coroutine, loop):
        self.coroutine = coroutine
        self.status = False  # Not ran yet
        self.joined = False
        self.result = None   # Updated when the coroutine execution ends
        self.loop = loop  # The EventLoop object that spawned the task
        self.cancelled = False
        self.execution = "INIT"

    def run(self):
        self.status = True
        return self.coroutine.send(None)

    def __repr__(self):
        return f"giambio.core.Task({self.coroutine}, {self.status}, {self.joined}, {self.result})"

    def throw(self, exception: Exception):
        self.result = Result(None, exception)
        return self.coroutine.throw(exception)

    async def cancel(self):
        return await cancel(self)

    async def join(self):
        return await join(self)

    def get_result(self):
        if self.result:
            if self.result.exc:
                raise self.result.exc
            else:
                return self.result.val


