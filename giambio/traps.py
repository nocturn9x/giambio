"""Helper methods to interact with the event loop"""

import types
import socket
from .abstractions import Task


@types.coroutine
def sleep(seconds: int):
    """Pause the execution of a coroutine for the passed amount of seconds,
    without blocking the entire event loop, which keeps watching for other events

    This function is also useful as a sort of checkpoint, because it returns the execution
    control to the scheduler, which can then switch to another task. If a coroutine does not have
    enough calls to async methods (or 'checkpoints'), e.g one that needs the 'await' keyword before it, this might
    affect performance as it would prevent the scheduler from switching tasks properly. If you feel
    like this happens in your code, try adding a call to giambio.sleep(0); this will act as a checkpoint without
    actually pausing the execution of your coroutine"""

    yield "want_sleep", seconds


@types.coroutine
def want_read(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to read from the passed socket"""

    yield "want_read", sock


@types.coroutine
def want_write(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to write into the passed socket"""

    yield "want_write", sock


@types.coroutine
def join(task: Task):
    """'Tells' the scheduler that the desired task MUST be awaited for completion"""

    task.joined = True
    yield "want_join", task
    return task.get_result()    # This raises an exception if the child task errored


@types.coroutine
def cancel(task: Task):
    """'Tells' the scheduler that the passed task must be cancelled"""

    yield "want_cancel", task

