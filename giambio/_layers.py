"""
Copyright (C) 2020 nocturn9x

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import types
from ._traps import join, cancel, event_set, event_wait

class Task:

    """A simple wrapper around a coroutine object"""

    def __init__(self, coroutine: types.coroutine):
        self.coroutine = coroutine
        self.cancelled = False   # True if the task gets cancelled
        self.exc = None
        self.result = None
        self.finished = False
        self.status = "init"  # This is useful for cancellation
        self._last_io = None
        self._notify = None

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

        return f"Task({self.coroutine}, cancelled={self.cancelled}, exc={repr(self.exc)}, result={self.result}, finished={self.finished}, status={self.status})"


class Event:
    """A class designed similarly to threading.Event, but with more features"""

    def __init__(self, loop):
        """Object constructor"""

        self._set = False
        self._notify = None
        self.notifier = loop.current_task
        self._timeout_expired = False
        self.event_caught = False
        self.timeout = None

    async def set(self, value=None):
        """Sets the event, optionally taking a value. This can be used
           to control tasks' flow by 'sending' commands back and fort"""

        self._set = True
        self._notify = value
        await event_set(self, value)

    async def pause(self, timeout=0):
        """Waits until the event is set and returns a value"""

        msg = await event_wait(self, timeout)
        if not self._timeout_expired:
            self.event_caught = True
        return msg
