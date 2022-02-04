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
from typing import Any
from giambio.traps import event_wait, event_set
from giambio.exceptions import GiambioError


class Event:
    """
    A class designed similarly to threading.Event
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
    An asynchronous queue similar to asyncio.Queue.
    NOT thread safe!
    """

    def __init__(self, maxsize: int):
        """
        Object constructor
        """

        self.events = {}
        self.container = []


    async def put(self, item: Any):
        """

        """
