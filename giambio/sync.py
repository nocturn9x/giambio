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
from giambio.traps import event_wait, event_set, current_task, suspend, schedule_tasks, current_loop
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

    async def trigger(self):
        """
        Sets the event, waking up all tasks that called
        pause() on it
        """

        if self.set:
            raise GiambioError("The event has already been set")
        await event_set(self)

    async def wait(self):
        """
        Waits until the event is set
        """

        await event_wait(self)


class Queue:
    """
    An asynchronous FIFO queue similar to asyncio.Queue
    that uses a collections.deque object for the underlying
    data representation. This queue is *NOT* thread-safe

    """

    def __init__(self, maxsize: Optional[int] = None):
        """
        Object constructor
        """

        self.maxsize = maxsize
        self.getters = deque()
        self.putters = deque()
        self.container = deque(maxlen=maxsize)


    async def put(self, item: Any):
        """
        Pushes an element onto the queue. If the
        queue is full, waits until there's 
        enough space for the queue
        """

        if not self.maxsize or len(self.container) < self.maxsize:
            if self.getters:
                task = self.getters.popleft()
                loop = await current_loop()
                loop._data[task] = item
                await schedule_tasks([task])
            else:
                self.container.append(item)
        else:
            self.putters.append(await current_task())
            print(self.putters)
            await suspend()
    

    async def get(self) -> Any:
        """
        Pops an element off the queue. Blocks until
        an element is put onto it again if the queue
        is empty
        """

        if self.container:
            if self.putters:
                await schedule_tasks([self.putters.popleft()])
            return self.container.popleft()
        else:
            self.getters.append(await current_task())
            return await suspend()