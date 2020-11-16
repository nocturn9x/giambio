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

# Implementation for all giambio traps, which are hooks
# into the event loop and allow it to switch tasks
# These coroutines are the one and only way to interact
# with the event loop from the user's perspective, and
# the entire library is based on these traps


import types


@types.coroutine
def create_trap(method, *args):
    """
    Creates and yields a trap. This
    is the lowest-level method to
    interact with the event loop
    """

    data = yield method, *args
    return data


async def sleep(seconds: int):
    """
    Pause the execution of an async function for a given amount of seconds,
    without blocking the entire event loop, which keeps watching for other events

    This function is also useful as a sort of checkpoint, because it returns
    control to the scheduler, which can then switch to another task. If your code
    doesn't have enough calls to async functions (or 'checkpoints') this might
    prevent the scheduler from switching tasks properly. If you feel like this
    happens in your code, try adding a call to giambio.sleep(0) somewhere.
    This will act as a checkpoint without actually pausing the execution
    of your function, but it will allow the scheduler to switch tasks

    :param seconds: The amount of seconds to sleep for
    :type seconds: int
    """

    assert seconds >= 0, "The time delay can't be negative"
    await create_trap("sleep", seconds)


async def current_task():
    """
    Gets the currently running task
    """

    return await create_trap("get_running")


async def join(task):
    """
    Awaits a given task for completion

    :param task: The task to join
    :type task: class: Task
    """

    return await create_trap("join", task, await current_task())


async def cancel(task):
    """
    Cancels the given task

    The concept of cancellation is tricky, because there is no real way to 'stop'
    a task if not by raising an exception inside it and ignoring whatever it
    returns (and also hoping that the task won't cause collateral damage). It
    is highly recommended that when you write async code you take into account
    that it might be cancelled at any time. You might think to just ignore the
    cancellation exception and be done with it, but doing so *will* break your
    code, so if you really wanna do that be sure to re-raise it when done!
    """

    await create_trap("cancel", task)
    assert task.cancelled, f"Coroutine ignored CancelledError"


async def want_read(stream):
    """
    Notifies the event loop that a task that wants to read from the given
    resource

    :param stream: The resource that needs to be read
    """

    await create_trap("want_read", stream)


async def want_write(stream):
    """
    Notifies the event loop that a task that wants to read from the given
    resource

    :param stream: The resource that needs to be written
    """

    await create_trap("want_write", stream)


async def event_set(event):
    """
    Communicates to the loop that the given event object
    must be set. This is important as the loop constantly
    checks for active events to deliver them
    """

    await create_trap("event_set", event)


async def event_wait(event):
    """
    Notifies the event loop that the current task has to wait
    for given event to trigger
    """

    await create_trap("event_wait", event)
