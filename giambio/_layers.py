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
from heapq import heappop, heappush
from .exceptions import GiambioError


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

    def __init__(self):
        """Object constructor"""

        self._set = False
        self._notify = None
        self.event_caught = False
        self.timeout = None
        self.waiting = 0

    async def set(self, value=True):
        """Sets the event, optionally taking a value. This can be used
           to control tasks' flow by 'sending' commands back and fort"""

        if self._set:
            raise GiambioError("The event has already been set")
        await event_set(self, value)

    async def pause(self):
        """Waits until the event is set and returns a value"""

        self.waiting += 1
        return await event_wait(self)


class TimeQueue:
    """An abstraction layer over a heap queue based on time. This is where
       sleeping tasks will be put when they are asleep"""

    def __init__(self, clock):
        self.clock = clock
        self.sequence = 0
        self.container = []

    def __contains__(self, item):
        return item in self.container

    def __iter__(self):
        return iter(self.container)

    def items(self):
        for _, __, item in self.container:
            yield item

    def __getitem__(self, item):
        return self.container.__getitem__(item)

    def __bool__(self):
        return bool(self.container)

    def __repr__(self):
        return f"TimeQueue({self.container}, clock={self.clock})"

    def put(self, item, amount):
        heappush(self.container, (self.clock() + amount, self.sequence, item))
        self.sequence += 1

    def get(self):
        return heappop(self.container)[2]


