import types
from .traps import _join, _cancel, _sleep


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
        self.status = False   # Not ran yet
        self.joined = False   # True if the task is joined
        self.result = None   # Updated when the coroutine execution ends
        self.loop = loop  # The EventLoop object that spawned the task
        self.cancelled = False   # True if the task gets cancelled
        self.execution = "INIT"   # Is set to 'FINISH' when the task ends
        self.steps = 0    # How many steps did the task run before ending, incremented while executing

    def run(self):
        """Simple abstraction layer over the coroutines ``send`` method"""

        self.status = True
        return self.coroutine.send(None)

    def __repr__(self):
        return f"giambio.core.Task({self.coroutine}, {self.status}, {self.joined}, {self.result})"

    def throw(self, exception: Exception):
        """Simple abstraction layer over the coroutines ``throw`` method"""

        self.result = Result(None, exception)
        return self.coroutine.throw(exception)

    async def cancel(self):
        """Cancels the task, throwing inside it a ``giambio.exceptions.CancelledError`` exception
        and discarding whatever the function could return"""

        await _sleep(0)  # Switch tasks (_sleep with 0 as delay merely acts as a checkpoint) or everything breaks: is it a good solution?
        return await _cancel(self)

    async def join(self, silent=False):
        return await _join(self, silent)

    def get_result(self, silenced=False):
        if self.result:
            if not silenced:
                if self.result.exc:
                    raise self.result.exc
                else:
                    return self.result.val
            return self.result.val if self.result.val else self.result.exc


