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
from typing import List, Tuple
from giambio.task import Task
from heapq import heappush, heappop, heapify


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

    def __len__(self):
        """
        Returns len(self)
        """

        return len(self.container)

    def __contains__(self, item: Task):
        """
        Implements item in self. This method behaves
        as if the queue only contained tasks and ignores
        their timeouts and tiebreakers
        """

        for i in self.container:
            if i[2] == item:
                return True
        return False

    def index(self, item: Task):
        """
        Returns the index of the given item in the list
        or -1 if it is not present
        """

        for i, e in enumerate(self.container):
            if e[2] == item:
                return i
        return -1

    def discard(self, item: Task):
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

    def __getitem__(self, item: int):
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
    An ordered queue for storing task deadlines
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
        if idx != -1:
            self.container.pop(idx)
            heapify(self.container)

    def get_closest_deadline(self) -> float:
        """
        Returns the closest deadline that is meant to expire
        or returns 0.0 if the queue is empty
        """

        if not self:
            return 0.0
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

    def __len__(self):
        """
        Returns len(self)
        """

        return len(self.container)

    def put(self, pool: "giambio.context.TaskManager"):
        """
        Pushes a pool with its deadline onto the queue. The
        timeout amount will be inferred from the pool object
        itself. Completed or expired pools are not added to the
        queue. Pools without a timeout are also ignored

        :param pool: The pool object to store
        """

        if pool and pool not in self.pools and not pool.done() and not pool.timed_out and pool.timeout:
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
