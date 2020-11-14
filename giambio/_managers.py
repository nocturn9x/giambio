"""
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

from ._core import AsyncScheduler
from ._layers import Task
import types


class TaskManager:
    """
    An asynchronous context manager for giambio
    """

    def __init__(self, loop: AsyncScheduler) -> None:
        """
        Object constructor
        """

        self.loop = loop

    def spawn(self, func: types.FunctionType, *args):
        """
        Spawns a child task
        """

        task = Task(func(*args))
        self.loop.tasks.append(task)
        return task

    def spawn_after(self, func: types.FunctionType, n: int, *args):
        """
        Schedules a task for execution after n seconds
        """

        assert n >= 0, "The time delay can't be negative"
        task = Task(func(*args))
        self.loop.paused.put(task, n)
        return task

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        for task in self.loop.tasks:
            try:
                await task.join()
            except BaseException as e:
                for running_task in self.loop.tasks:
                    await running_task.cancel()
                for _, __, asleep_task in self.loop.paused:
                    await asleep_task.cancel()
                for waiting_tasks in self.loop.event_waiting.values():
                    for waiting_task in waiting_tasks:
                        await waiting_task.cancel()
                raise e
