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
from .core import AsyncScheduler
from .objects import Task


class TaskManager:
    """
    An asynchronous context manager for giambio
    """

    def __init__(self, loop: AsyncScheduler) -> None:
        """
        Object constructor
        """

        self.loop = loop
        self.tasks = []

    def spawn(self, func: types.FunctionType, *args):
        """
        Spawns a child task
        """

        task = Task(func(*args), func.__name__ or str(func))
        task.parent = self.loop.current_task
        self.loop.tasks.append(task)
        self.tasks.append(task)
        self.loop.debugger.on_task_spawn(task)

    def spawn_after(self, func: types.FunctionType, n: int, *args):
        """
        Schedules a task for execution after n seconds
        """

        assert n >= 0, "The time delay can't be negative"
        task = Task(func(*args), func.__name__ or str(func))
        task.parent = self.loop.current_task
        task.sleep_start = self.loop.clock()
        self.loop.paused.put(task, n)
        self.tasks.append(task)
        self.loop.debugger.on_task_schedule(task, n)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        for task in self.tasks:
            try:
                await task.join()
            except BaseException:
                self.tasks.remove(task)
                for to_cancel in self.tasks:
                    await to_cancel.cancel()