from collections import deque
from .exceptions import CancelledError
import types
from .abstractions import Task
from heapq import heappush


class TaskManager:
    """Class to be used inside context managers to spawn multiple tasks and be sure that they will all joined before the code exits the with block"""


    def __init__(self, loop, silent=False):
        self.tasks = deque()    # All tasks spawned
        self.values = {}   # Results OR exceptions of each task
        self.loop = loop   # The event loop that spawned the TaskManager
        self.silent = silent   # Make exceptions silent? (not recommended)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        for task in self.tasks:
            if task.cancelled:
                self.values[task] = CancelledError()
            else:
                self.values[task] = await task.join(self.silent)

    def spawn(self, coroutine: types.coroutine):
        """Schedules a task for execution, appending it to the call stack"""

        task = Task(coroutine, self)
        self.loop.to_run.append(task)
        return task

    def schedule(self, coroutine: types.coroutine, when: int):
        """Schedules a task for execution after n seconds"""

        self.loop.sequence += 1
        task = Task(coroutine, self)
        heappush(self.loop.paused, (self.loop.clock() + when, self.loop.sequence, task))
        return task
