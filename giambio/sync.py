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
from socket import socketpair
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Optional
from giambio.traps import event_wait, event_set, current_task
from giambio.exceptions import GiambioError
from giambio.socket import wrap_socket
from giambio.task import Task


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
        # Stores event objects for tasks wanting to
        # get items from the queue
        self.getters = deque()
        # Stores event objects for tasks wanting to 
        # put items on the queue
        self.putters = deque()
        self.container = deque()

    def __len__(self):
        """
        Returns the length of the queue
        """

        return len(self.container)
    

    def __repr__(self) -> str:
        return f"{type(self).__name__}({f', '.join(map(str, self.container))})"

    async def __aiter__(self):
        """
        Implements the asynchronous iterator protocol
        """

        return self
    
    async def __anext__(self):
        """
        Implements the asynchronous iterator protocol
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


class Channel(ABC):
    """
    A generic, two-way, full-duplex communication channel between
    tasks. This is just an abstract base class!
    """

    def __init__(self, maxsize: Optional[int] = None):
        """
        Public object constructor
        """

        self.maxsize = maxsize
        self.closed = False
    
    @abstractmethod
    async def write(self, data: str):
        """
        Writes data to the channel. Blocks if the internal
        queue is full until a spot is available. Does nothing
        if the channel has been closed
        """

        return NotImplemented

    @abstractmethod
    async def read(self):
        """
        Reads data from the channel. Blocks until
        a message arrives or returns immediately if
        one is already waiting
        """

        return NotImplemented
    
    @abstractmethod
    async def close(self):
        """
        Closes the memory channel. Any underlying
        data is left for other tasks to read
        """

        return NotImplemented
   
    @abstractmethod 
    async def pending(self):
        """
        Returns if there's pending
        data to be read
        """

        return NotImplemented


class MemoryChannel(Channel):
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

        super().__init__(maxsize)
        # We use a queue as our buffer
        self.buffer = Queue(maxsize=maxsize)


    async def write(self, data: str):
        """
        Writes data to the channel. Blocks if the internal
        queue is full until a spot is available. Does nothing
        if the channel has been closed
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
        data is left for other tasks to read
        """

        self.closed = True
    
    async def pending(self):
        """
        Returns if there's pending
        data to be read
        """

        return bool(len(self.buffer))


class NetworkChannel(Channel):
    """
    A two-way communication channel between tasks based
    on giambio's I/O mechanisms instead of in-memory queues
    """

    def __init__(self):
        """
        Public object constructor
        """

        super().__init__(None)
        # We use a socket as our buffer instead of a queue
        sockets = socketpair()
        self.reader = wrap_socket(sockets[0])
        self.writer = wrap_socket(sockets[1])
        self._internal_buffer = b""


    async def write(self, data: bytes):
        """
        Writes data to the channel. Blocks if the internal
        socket is not currently available. Does nothing
        if the channel has been closed
        """

        if self.closed:
            return
        await self.writer.send_all(data)

    async def read(self, size: int):
        """
        Reads exactly size bytes from the channel. Blocks until
        enough data arrives. Extra data is cached and used on the
        next read
        """

        data = self._internal_buffer
        while len(data) < size:
            data += await self.reader.receive(size)
        self._internal_buffer = data[size:]
        data = data[:size]
        return data
    
    async def close(self):
        """
        Closes the memory channel. Any underlying
        data is flushed out of the internal socket
        and is lost
        """

        self.closed = True
        await self.reader.close()
        await self.writer.close()
    
    async def pending(self):
        """
        Returns if there's pending
        data to be read
        """
        
        # TODO: Ugly!
        if self.closed:
            return False
        try:
            self._internal_buffer += self.reader.sock.recv(1)
        except BlockingIOError:
            return False
        return True


class Lock:
    """
    A simple single-owner lock
    """

    def __init__(self):
        """
        Public constructor
        """

        self.owner: Optional[Task] = None
        self.tasks: deque[Event] = deque()

    async def acquire(self):
        """
        Acquires the lock
        """

        task = await current_task()
        if self.owner is None:
            self.owner = task
        elif task is self.owner:
            raise RuntimeError("lock is already acquired by current task")
        elif self.owner is not task:
            self.tasks.append(Event())
            await self.tasks[-1].wait()
            self.owner = task

    async def release(self):
        """
        Releases the lock
        """

        task = await current_task()
        if self.owner is None:
            raise RuntimeError("lock is not acquired")
        elif self.owner is not task:
            raise RuntimeError("lock can only released by its owner")
        elif self.tasks:
            await self.tasks.popleft().trigger()
        else:
            self.owner = None


    async def __aenter__(self):
        await self.acquire()
        return self
    

    async def __aexit__(self, *args):
        await self.release()
