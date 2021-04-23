"""
Various object wrappers and abstraction layers for internal use

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

import giambio
from dataclasses import dataclass, field
from heapq import heappop, heappush, heapify
from typing import Union, Coroutine, List, Tuple


@dataclass
class Task:

    """
    A simple wrapper around a coroutine object
    """

    # The name of the task. Usually this equals self.coroutine.__name__,
    # but in some cases it falls back to repr(self.coroutine)
    name: str
    # The underlying coroutine object to wrap around a giambio task
    coroutine: Coroutine
    # The async pool that spawned this task. The one and only task that hasn't
    # an associated pool is the main entry point which is not available externally
    pool: Union["giambio.context.TaskManager", None] = None
    # Whether the task has been cancelled or not. This is True both when the task is
    # explicitly cancelled via its cancel() method or when it is cancelled as a result
    # of an exception in another task in the same pool
    cancelled: bool = False
    # This attribute will be None unless the task raised an error
    exc: BaseException = None
    # The return value of the coroutine
    result: object = None
    # This attribute signals that the task has exited normally (returned)
    finished: bool = False
    # This attribute represents what the task is doing and is updated in real
    # time by the event loop, internally. Possible values for this are "init"--
    # when the task has been created but not started running yet--, "run"-- when
    # the task is running synchronous code--, "io"-- when the task is waiting on
    # an I/O resource--, "sleep"-- when the task is either asleep or waiting on an event
    # and "crashed"-- when the task has exited because of an exception
    status: str = "init"
    # This attribute counts how many times the task's run() method has been called
    steps: int = 0
    # Simple optimization to improve the selector's efficiency. Check AsyncScheduler.register_sock
    # inside giambio.core to know more about it
    last_io: tuple = ()
    # All the tasks waiting on this task's completion
    joiners: list = field(default_factory=list)
    # Whether this task has been waited for completion or not. The one and only task
    # that will have this attribute set to False is the main program entry point, since
    # the loop will implicitly wait for anything else to complete before returning
    joined: bool = False
    # Whether this task has a pending cancellation scheduled. Check AsyncScheduler.cancel
    # inside giambio.core to know more about this attribute
    cancel_pending: bool = False
    # Absolute clock time that represents the date at which the task started sleeping,
    # mainly used for internal purposes and debugging
    sleep_start: float = 0.0
    # The next deadline, in terms of the absolute clock of the loop, associated to the task
    next_deadline: float = 0.0

    def run(self, what: object = None):
        """
        Simple abstraction layer over coroutines' ``send`` method

        :param what: The object that has to be sent to the coroutine,
        defaults to None
        :type what: object, optional
        """

        return self.coroutine.send(what)

    def throw(self, err: Exception):
        """
        Simple abstraction layer over coroutines ``throw`` method

        :param err: The exception that has to be raised inside
        the task
        :type err: Exception
        """

        return self.coroutine.throw(err)

    async def join(self):
        """
        Pauses the caller until the task has finished running.
        Any return value is passed to the caller and exceptions
        are propagated as well
        """

        res = await giambio.traps.join(self)
        if self.exc:
            raise self.exc
        return res

    async def cancel(self):
        """
        Cancels the task
        """

        await giambio.traps.cancel(self)

    def __hash__(self):
        """
        Implements hash(self)
        """

        return hash(self.coroutine)

    def done(self):
        """
        Returns True if the task is not running,
        False otherwise
        """

        return self.exc or self.finished or self.cancelled


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
        pause() on it
        """

        if self.set:  # This is set by the event loop internally
            raise giambio.exceptions.GiambioError("The event has already been set")
        await giambio.traps.event_set(self)

    async def wait(self):
        """
        Waits until the event is set
        """

        await giambio.traps.event_wait(self)


class TimeQueue:
    """
    An abstraction layer over a heap queue based on time. This is where
    sleeping tasks will be put when they are not running

    :param clock: The same monotonic clock that was passed to the thread-local event loop.
    It is important for the queue to be synchronized with the loop as this allows
    the sleeping mechanism to work reliably
    """

    def __init__(self, clock):
        """
        Object constructor
        """

        self.clock = clock
        # The sequence number handles the race condition
        # of two tasks with identical deadlines, acting
        # as a tie breaker
        self.sequence = 0
        self.container: List[Tuple[float, int, Task]] = []

    def __contains__(self, item):
        """
        Implements item in self. This method behaves
        as if the queue only contained tasks and ignores
        their timeouts and tiebreakers
        """

        for i in self.container:
            if i[2] == item:
                return True
        return False

    def index(self, item):
        """
        Returns the index of the given item in the list
        or -1 if it is not present
        """

        for i, e in enumerate(self.container):
            if e[2] == item:
                return i
        return -1

    def discard(self, item):
        """
        Discards an item from the queue and
        calls heapify(self.container) to keep
        the heap invariant if an element is removed.
        This method does nothing if the item is not
        in the queue, but note that in this case the
        operation would still take O(n) iterations
        to complete

        :param item: The item to be discarded
        """

        idx = self.index(item)
        if idx != -1:
            self.container.pop(idx)
            heapify(self.container)

    def get_closest_deadline(self) -> float:
        """
        Returns the closest deadline that is meant to expire
        or raises IndexError if the queue is empty
        """

        if not self:
            raise IndexError("TimeQueue is empty")
        return self.container[0][0]

    def __iter__(self):
        """
        Implements iter(self)
        """

        return self

    def __next__(self):
        """
        Implements next(self)
        """

        try:
            return self.get()
        except IndexError:
            raise StopIteration from None

    def __getitem__(self, item):
        """
        Implements self[n]
        """

        return self.container.__getitem__(item)

    def __bool__(self):
        """
        Implements bool(self)
        """

        return bool(self.container)

    def __repr__(self):
        """
        Implements repr(self) and str(self)
        """

        return f"TimeQueue({self.container}, clock={self.clock})"

    def put(self, task: Task, amount: float):
        """
        Pushes a task onto the queue together with its
        sleep amount

        :param task: The task that is meant to sleep
        :type task: :class: Task
        :param amount: The amount of time, in seconds, that the
        task should sleep for
        :type amount: float
        """

        heappush(self.container, (self.clock() + amount, self.sequence, task))
        self.sequence += 1

    def get(self) -> Task:
        """
        Gets the first task that is meant to run

        :raises: IndexError if the queue is empty
        """

        if not self.container:
            raise IndexError("get from empty TimeQueue")
        return heappop(self.container)[2]


class DeadlinesQueue:
    """
    An ordered queue for storing tasks deadlines
    """

    def __init__(self):
        """
        Object constructor
        """

        self.pools = set()
        self.container: List[Tuple[float, int, giambio.context.TaskManager]] = []
        self.sequence = 0

    def __contains__(self, item):
        """
        Implements item in self. This method behaves
        as if the queue only contained tasks and ignores
        their timeouts and tiebreakers
        """

        for i in self.container:
            if i[2] == item:
                return True
        return False

    def index(self, item):
        """
        Returns the index of the given item in the list
        or -1 if it is not present
        """

        for i, e in enumerate(self.container):
            if e[2] == item:
                return i
        return -1

    def discard(self, item):
        """
        Discards an item from the queue and
        calls heapify(self.container) to keep
        the heap invariant if an element is removed.
        This method does nothing if the item is not
        in the queue, but note that in this case the
        operation would still take O(n) iterations
        to complete

        :param item: The item to be discarded
        """

        idx = self.index(item)
        if idx != 1:
            self.container.pop(idx)
            heapify(self.container)

    def get_closest_deadline(self) -> float:
        """
        Returns the closest deadline that is meant to expire
        or raises IndexError if the queue is empty
        """

        if not self:
            raise IndexError("DeadlinesQueue is empty")
        return self.container[0][0]

    def __iter__(self):
        """
        Implements iter(self)
        """

        return self

    def __next__(self):
        """
        Implements next(self)
        """

        try:
            return self.get()
        except IndexError:
            raise StopIteration from None

    def __getitem__(self, item):
        """
        Implements self[n]
        """

        return self.container.__getitem__(item)

    def __bool__(self):
        """
        Implements bool(self)
        """

        return bool(self.container)

    def __repr__(self):
        """
        Implements repr(self) and str(self)
        """

        return f"DeadlinesQueue({self.container})"

    def put(self, pool: "giambio.context.TaskManager"):
        """
        Pushes a pool with its deadline onto the queue. The
        timeout amount will be inferred from the pool object
        itself

        :param pool: The pool object to store
        """

        if pool not in self.pools:
            self.pools.add(pool)
            heappush(self.container, (pool.timeout, self.sequence, pool))
            self.sequence += 1

    def get(self) -> "giambio.context.TaskManager":
        """
        Gets the first pool that is meant to expire

        :raises: IndexError if the queue is empty
        """

        if not self.container:
            raise IndexError("get from empty DeadlinesQueue")
        d = heappop(self.container)
        self.pools.discard(d[2])
        return d[2]
