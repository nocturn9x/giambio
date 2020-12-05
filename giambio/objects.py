"""
Various object wrappers and abstraction layers

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

from giambio.traps import join, cancel, event_set, event_wait
from heapq import heappop, heappush
from giambio.exceptions import GiambioError
from dataclasses import dataclass, field
import typing


@dataclass
class Task:

    """
    A simple wrapper around a coroutine object
    """

    coroutine: typing.Coroutine
    name: str
    pool: "giambio.context.TaskManager"
    cancelled: bool = False
    exc: BaseException = None
    result: object = None
    finished: bool = False
    status: str = "init"
    steps: int = 0
    last_io: tuple = ()
    joiners: list = field(default_factory=list)
    joined: bool = False
    cancel_pending: bool = False
    sleep_start: float = 0.0
    next_deadline: float = 0.0

    def run(self, what: object = None):
        """
        Simple abstraction layer over coroutines' ``send`` method
        """

        return self.coroutine.send(what)

    def throw(self, err: Exception):
        """
        Simple abstraction layer over coroutines ``throw`` method
        """

        return self.coroutine.throw(err)

    async def join(self):
        """
        Joins the task
        """

        res = await join(self)
        if self.exc:
            raise self.exc
        return res

    async def cancel(self):
        """
        Cancels the task
        """

        await cancel(self)

    def __hash__(self):
        return hash(self.coroutine)


class Event:
    """
    A class designed similarly to threading.Event
    """

    def __init__(self):
        """
        Object constructor
        """

        self.set = False
        self.waiters = []
        self.event_caught = False

    async def trigger(self):
        """
        Sets the event, waking up all tasks that called
        pause() on us
        """

        if self.set:
            raise GiambioError("The event has already been set")
        await event_set(self)

    async def wait(self):
        """
        Waits until the event is set
        """

        await event_wait(self)


class TimeQueue:
    """
    An abstraction layer over a heap queue based on time. This is where
    sleeping tasks will be put when they are not running
    """

    def __init__(self, clock):
        """
        Object constructor
        """

        self.clock = clock
        self.sequence = 0
        # The sequence number handles the race condition
        # of two tasks with identical deadlines acting
        # as a tie breaker
        self.container = []

    def __contains__(self, item):
        return item in self.container

    def __iter__(self):
        return self
    
    def __next__(self):
        try:
            return self.get()
        except IndexError:
            raise StopIteration from None

    def __getitem__(self, item):
        return self.container.__getitem__(item)

    def __bool__(self):
        return bool(self.container)

    def __repr__(self):
        return f"TimeQueue({self.container}, clock={self.clock})"

    def put(self, item, amount: float):
        """
        Pushes an item onto the queue with its unique
        time amount and ID
        """

        heappush(self.container, (self.clock() + amount, self.sequence, item))
        self.sequence += 1

    def get(self):
        """
        Gets the first task that is meant to run
        """

        return heappop(self.container)[2]


class DeadlinesQueue(TimeQueue):
    """
    An ordered queue for storing tasks deadlines
    """

    def __init__(self):
        """
        Object constructor
        """

        super().__init__(None)

    def __contains__(self, item):
        return super().__contains__(item)

    def __iter__(self):
        return super().__iter__()

    def __next__(self):
        return super().__next__()

    def __getitem__(self, item):
        return super().__getitem__(item)

    def __bool__(self):
        return super().__bool__()

    def __repr__(self):
        return f"DeadlinesQueue({self.container})"

    def put(self, amount: float):
        """
        Pushes a deadline (timeout) onto the queue
        """

        heappush(self.container, (amount, self.sequence))
        self.sequence += 1

    def get(self):
        """
        Gets the first task that is meant to run
        """

        return super().get()
