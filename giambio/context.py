"""
Higher-level context managers for async pools

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
from giambio.objects import Task
from giambio.core import AsyncScheduler


class TaskManager:
    """
    An asynchronous context manager for giambio
    """

    def __init__(self, loop: AsyncScheduler, timeout: float = None) -> None:
        """
        Object constructor
        """

        self.loop = loop
        self.tasks = []  # We store a reference to all tasks in this pool, even the paused ones!
        self.cancelled = False
        self.started = self.loop.clock()
        if timeout:
            self.timeout = self.started + timeout
        else:
            self.timeout = None
        self.timed_out = False

    def spawn(self, func: types.FunctionType, *args):
        """
        Spawns a child task
        """

        task = Task(func(*args), func.__name__ or str(func), self)
        task.joiners = [self.loop.current_task]
        task.next_deadline = self.timeout or 0.0
        self.loop.tasks.append(task)
        self.loop.debugger.on_task_spawn(task)
        self.tasks.append(task)
        return task

    def spawn_after(self, func: types.FunctionType, n: int, *args):
        """
        Schedules a task for execution after n seconds
        """

        assert n >= 0, "The time delay can't be negative"
        task = Task(func(*args), func.__name__ or str(func), self)
        task.joiners = [self.loop.current_task]
        task.next_deadline = self.timeout or 0.0
        task.sleep_start = self.loop.clock()
        self.loop.paused.put(task, n)
        self.loop.debugger.on_task_schedule(task, n)
        self.tasks.append(task)
        return task

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type: Exception, exc: Exception, tb):
        for task in self.tasks:
            # This forces Python to stop at the
            # end of the block and wait for all
            # children to exit
            await task.join()

    async def cancel(self):
        """
        Cancels the whole block
        """

        # TODO: This breaks, somehow, investigation needed
        for task in self.tasks:
            await task.cancel()

    def done(self):
        return all([task.done() for task in self.tasks])
