"""
Task synchronization primitives

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
from collections import deque
from typing import Any, Optional
from giambio.traps import event_wait, event_set
from giambio.exceptions import GiambioError


class Event:
    """
    A class designed similarly to threading.Event (not
    thread-safe though)
    """

    def __init__(self):
        """
        Object constructor
        """

        self.set = False
        self.waiters = set()
        self.value = None

    async def trigger(self, value: Optional[Any] = None):
        """
        Sets the event, waking up all tasks that called
        pause() on it
        """

        if self.set:
            raise GiambioError("The event has already been set")
        self.value = value
        await event_set(self, value)

    async def wait(self):
        """
        Waits until the event is set
        """

        return await event_wait(self)


class Queue:
    """
    An asynchronous FIFO queue similar to asyncio.Queue
    that uses a collections.deque object for the underlying
    data representation. This queue is *NOT* thread-safe as
    it is based on giambio's Event mechanism
    """

    def __init__(self, maxsize: Optional[int] = None):
        """
        Object constructor
        """

        self.maxsize = maxsize
        self.getters = deque()
        self.putters = deque()
        self.container = deque()

    def __len__(self):
        """
        Returns the length of the queue
        """

        return len(self.container)
    

    async def __aiter__(self):
        """
        Implements the iterator protocol
        """

        return self
    
    async def __anext__(self):
        """
        Implements the iterator protocol
        """

        return await self.get()

    async def put(self, item: Any):
        """
        Pushes an element onto the queue. If the
        queue is full, waits until there's 
        enough space for the queue
        """

        if not self.maxsize or len(self.container) < self.maxsize:
            self.container.append(item)
            if self.getters:
                await self.getters.popleft().trigger(self.container.popleft())
        else:
            ev = Event()
            self.putters.append(ev)
            await ev.wait()
            self.container.append(item)

    async def get(self) -> Any:
        """
        Pops an element off the queue. Blocks until
        an element is put onto it again if the queue
        is empty
        """

        if self.container:
            if self.putters:
                await self.putters.popleft().trigger()
            return self.container.popleft()
        else:
            ev = Event()
            self.getters.append(ev)
            return await ev.wait()

    async def clear(self):
        """
        Clears the queue 
        """

        self.container.clear()

    async def reset(self):
        """
        Resets the queue
        """

        await self.clear()
        self.getters.clear()
        self.putters.clear()


class MemoryChannel:
    """
    A two-way communication channel between tasks based
    on giambio's queueing mechanism. Operations on this
    object do not perform any I/O or other system call and
    are therefore extremely efficient
    """

    def __init__(self, maxsize: Optional[int] = None):
        """
        Public object constructor
        """

        # We use a queue as our buffer
        self.buffer = Queue(maxsize=maxsize)
        self.maxsize = maxsize
        self.closed = False


    async def write(self, data: str):
        """
        Writes data to the channel. Blocks if the internal
        queue is full until a spot is available
        """

        if self.closed:
            return
        await self.buffer.put(data)

    async def read(self):
        """
        Reads data from the channel. Blocks until
        a message arrives or returns immediately if
        one is already waiting
        """

        return await self.buffer.get()
    
    async def close(self):
        """
        Closes the memory channel. Any underlying
        data is left for clients to read
        """

        self.closed = True
    
    async def pending(self):
        """
        Returns if there's pending
        data to be read
        """

        return bool(len(self.buffer))