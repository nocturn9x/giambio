from collections import deque
import types
from ._layers import Task
from heapq import heappush


class TaskManager:
    """The only way to execute asynchronous code in giambio is trough a ``TaskManager`` (or one of its children classes) object used within
    an ``async with`` context manager. The ``TaskManager`` is an ideal "playground" where all asynchronous code runs and where giambio's 
    event loop can control their execution flow.

    The key feature of this mechanism is that all tasks are always joined automatically: This opens a new world of features,
    allowing exceptions to propagate just as expected (exceptions are **never** discarded in giambio, unlike in some other libraries) and some other lower-level advantages.
    Moreover, giambio always saves the return values so that you don't lose any important information when executing a coroutine.

    There are a few concepts to explain here, though:

        - The term "task" refers to a coroutine executed trough the ``TaskManager``'s methods ``spawn()`` and ``schedule()``, as well as
        one executed with ``await coro()``
        - If an exception occurs, all other tasks are cancelled (read more below) and the exception is later propagated in the parent task
        - The concept of cancellation is a bit tricky, because there is no real way to stop a coroutine from executing without actually raising
        an exception inside i. So when giambio needs to cancel a task, it just throws ``giambio.exceptions.CancelledError`` inside it and hopes for the best.
        This exception inherits from ``BaseException``, which by convention means that it should not be catched. Doing so in giambio will likely break your code
        and make it explode spectacularly. If you really want to catch it to perform cleanup, be sure to re-raise it when done (or to raise another unhandled exception if you want)
        so that the internal loop can proceed with execution.
        In general, when writing an asynchronous function, you should always consider that it might be cancelled at any time and handle that case accordingly.
    """

    def __init__(self, loop):
        self.values = {}   # Results from each task
        self.loop = loop   # The event loop that spawned the TaskManager

    async def _cancel_and_raise(self, exc):
        """Cancels all the tasks inside the TaskManager object and raises the exception
        of the task that triggered this mechanism"""

        try:
            await self.loop.running.cancel()
        except Exception as error:
           self.loop.running.exc = error
        for task in self.loop.to_run + deque(self.loop.paused):
            if isinstance(task, tuple):   # Sleeping task
                _, _, task = task
            try:
                await task.cancel()
            except Exception as error:
                task.exc = error
            raise exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        while True:
            if not any([self.loop.to_run, self.loop.paused]):
                break
            tasks = self.loop.to_run + deque(self.loop.paused)
            task = tasks.popleft()
            if isinstance(task, tuple):   # Sleeping task
                _, _, task = task
            self.values[task] = await task.join()
            if task.exc:
                print(task)
                await self._cancel_and_raise(task.exc)

    def spawn(self, coroutine: types.coroutine):
        """Schedules a task for execution, appending it to the call stack

           :param coroutine: The coroutine to spawn, please note that if you want to execute foo, you need to pass foo() as this
           returns a coroutine instead of a function object
           :type coroutine: types.coroutine
           :returns: A ``Task`` object
           :rtype: class: Task
        """

        task = Task(coroutine)
        self.loop.to_run.append(task)
        return task

    def schedule(self, coroutine: types.coroutine, n: int):
        """Schedules a task for execution after when seconds

           :param coroutine: The coroutine to spawn, please note that if you want to execute foo, you need to pass foo() as this
           returns a coroutine instead of a function object
           :type coroutine: types.coroutine
           :param n: The delay in seconds after which the task should start running
           :type n: int
           :returns: A ``Task`` object
           :rtype: class: Task
        """

        self.loop.sequence += 1
        task = Task(coroutine)
        heappush(self.loop.paused, (self.loop.clock() + n, self.loop.sequence, task))
        return task
