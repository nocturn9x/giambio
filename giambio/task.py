"""
Object wrapper for asynchronous tasks

Copyright (C) 2020 nocturn9x

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import giambio
import warnings
from dataclasses import dataclass, field
from typing import Union, Coroutine, Set


@dataclass
class Task:

    """
    A simple wrapper around a coroutine object
    """

    # The name of the task. Usually this equals self.coroutine.__name__,
    # but it may fall back to repr(self.coroutine)
    name: str
    # The underlying coroutine object to wrap around a giambio task
    coroutine: Coroutine
    # The async pool that spawned this task. The one and only task which may have
    # no associated pool is the main entry point which is not available externally
    # (but if a pool is started in the main task, it somewhat becomes part of that
    # pool as its parent)
    pool: Union["giambio.context.TaskManager", None] = None
    # Whether the task has been cancelled or not. This is True both when the task is
    # explicitly cancelled via its cancel() method or when it is cancelled as a result
    # of an exception in another task
    cancelled: bool = False
    # This attribute will be None unless the task raised an error
    exc: BaseException = None
    # The return value of the coroutine
    result: object = None
    # This attribute signals that the task has exited normally (returned)
    finished: bool = False
    # This attribute represents what the task is doing and is updated in real
    # time by the event loop, internally. Possible values for this are "init"--
    # when the task has been created but not started running yet--, "run"-- when
    # the task is running synchronous code--, "io"-- when the task is waiting on
    # an I/O resource--, "sleep"-- when the task is either asleep, waiting on
    # an event or otherwise suspended, "crashed"-- when the task has exited because 
    # of an exception and "cancelled" when-- when the task has been explicitly cancelled 
    # with its cancel() method or as a result of an exception
    status: str = "init"
    # This attribute counts how many times the task's run() method has been called
    steps: int = 0
    # Simple optimization to improve the selector's efficiency. Check AsyncScheduler.register_sock
    # inside giambio.core to know more about it
    last_io: tuple = ()
    # All the tasks waiting on this task's completion
    joiners: Set = field(default_factory=set)
    # Whether this task has been waited for completion or not. The one and only task
    # that will have this attribute set to False is the main program entry point, since
    # the loop will implicitly wait for anything else to complete before returning
    joined: bool = False
    # Whether this task has a pending cancellation scheduled. Check AsyncScheduler.cancel
    # inside giambio.core to know more about this attribute
    cancel_pending: bool = False
    # Absolute clock time that represents the date at which the task started sleeping,
    # mainly used for internal purposes and debugging
    sleep_start: float = 0.0
    # The next deadline, in terms of the absolute clock of the loop, associated to the task
    next_deadline: float = 0.0

    def run(self, what: object = None):
        """
        Simple abstraction layer over coroutines' ``send`` method

        :param what: The object that has to be sent to the coroutine,
        defaults to None
        :type what: object, optional
        """

        return self.coroutine.send(what)

    def throw(self, err: Exception):
        """
        Simple abstraction layer over coroutines ``throw`` method

        :param err: The exception that has to be raised inside
        the task
        :type err: Exception
        """

        # self.exc = err
        return self.coroutine.throw(err)

    async def join(self):
        """
        Pauses the caller until the task has finished running.
        Any return value is passed to the caller and exceptions
        are propagated as well
        """

        if task := await giambio.traps.current_task():
            self.joiners.add(task)
        return await giambio.traps.join(self)


    async def cancel(self):
        """
        Cancels the task
        """

        await giambio.traps.cancel(self)

    def __hash__(self):
        """
        Implements hash(self)
        """

        return hash(self.coroutine)

    def done(self):
        """
        Returns True if the task is not running,
        False otherwise
        """

        return self.exc or self.finished or self.cancelled

    def __del__(self):
        """
        Task destructor
        """

        try:
            self.coroutine.close()
        except RuntimeError:
            pass  # TODO: This is kinda bad
        if self.last_io:
            warnings.warn(f"task '{self.name}' was destroyed, but has pending I/O")
