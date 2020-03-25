from .abstractions import Task
from collections import deque


class TaskManager(Task):
    """Class to be used inside context managers to spawn multiple tasks and be sure that they will all joined before the code exits the with block"""


    def __init__(self, loop):
        self.tasks = deque()    # All tasks spawned
        self.values = {}   # Results OR exceptions of each task
        self.loop = loop

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        for task in self.tasks:
            self.values[task.coroutine.__name__] = await task.join()

    async def spawn(self, coro):
        task = self.loop.spawn(coro)
        self.tasks.append(task)
        return task

    async def schedule(self, coro, delay):
        task = self.loop.schedule(coro, delay)
        self.tasks.append(task)
        return task
