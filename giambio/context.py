"""
Higher-level context manager(s) for async pools

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
import types
from typing import List


class TaskManager:
    """
    An asynchronous context manager for giambio, similar to trio's nurseries

    :param timeout: The pool's timeout length in seconds, if any, defaults to None
    :type timeout: float, optional
    """

    def __init__(self, timeout: float = None) -> None:
        """
        Object constructor
        """

        # The event loop associated with this pool
        self.loop: giambio.core.AsyncScheduler = giambio.get_event_loop()
        # All the tasks that belong to this pool
        self.tasks: List[giambio.objects.Task] = []
        # Whether we have been cancelled or not
        self.cancelled: bool = False
        # The clock time of when we started running, used for
        # timeouts expiration
        self.started: float = self.loop.clock()
        # The pool's timeout (in seconds)
        if timeout:
            self.timeout: float = self.started + timeout
        else:
            self.timeout: None = None
        # Whether our timeout expired or not
        self.timed_out: bool = False

    def spawn(self, func: types.FunctionType, *args) -> "giambio.objects.Task":
        """
        Spawns a child task
        """

        task = giambio.objects.Task(func.__name__ or str(func), func(*args), self)
        task.joiners = [self.loop.current_task]
        task.next_deadline = self.timeout or 0.0
        self.loop.tasks.append(task)
        self.loop.debugger.on_task_spawn(task)
        self.tasks.append(task)
        return task

    def spawn_after(self, func: types.FunctionType, n: int, *args) -> "giambio.objects.Task":
        """
        Schedules a task for execution after n seconds
        """

        assert n >= 0, "The time delay can't be negative"
        task = giambio.objects.Task(func.__name__ or str(func), func(*args), self)
        task.joiners = [self.loop.current_task]
        task.next_deadline = self.timeout or 0.0
        task.sleep_start = self.loop.clock()
        self.loop.paused.put(task, n)
        self.loop.debugger.on_task_schedule(task, n)
        self.tasks.append(task)
        return task

    async def __aenter__(self):
        """
        Implements the asynchronous context manager interface,
        """

        return self

    async def __aexit__(self, exc_type: Exception, exc: Exception, tb):
        """
        Implements the asynchronous context manager interface, joining
        all the tasks spawned inside the pool
        """

        for task in self.tasks:
            # This forces the interpreter to stop at the
            # end of the block and wait for all
            # children to exit
            await task.join()

    async def cancel(self):
        """
        Cancels the pool entirely, iterating over all
        the pool's tasks and cancelling them
        """

        # TODO: This breaks, somehow, investigation needed
        for task in self.tasks:
            await task.cancel()

    def done(self) -> bool:
        """
        Returns True if all the tasks inside the
        pool have exited, False otherwise
        """

        return all([task.done() for task in self.tasks])
