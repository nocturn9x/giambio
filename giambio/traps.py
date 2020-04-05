"""Helper methods to interact with the event loop"""

import types
import socket


@types.coroutine
def _sleep(seconds: int):
    """Pause the execution of a coroutine for the passed amount of seconds,
    without blocking the entire event loop, which keeps watching for other events

    This function is also useful as a sort of checkpoint, because it returns the execution
    control to the scheduler, which can then switch to another task. If a coroutine does not have
    enough calls to async methods (or 'checkpoints'), e.g one that needs the 'await' keyword before it, this might
    affect performance as it would prevent the scheduler from switching tasks properly. If you feel
    like this happens in your code, try adding a call to giambio.sleep(0); this will act as a checkpoint without
    actually pausing the execution of your coroutine

    :param seconds: The amount of seconds to sleep for
    :type seconds: int
    """

    yield "want_sleep", seconds


@types.coroutine
def _want_read(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to read from the passed socket

       :param sock: The socket to perform the operation on
       :type sock: class: socket.socket
    """

    yield "want_read", sock


@types.coroutine
def _want_write(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to write into the passed socket

       :param sock: The socket to perform the operation on
       :type sock: class: socket.socket
    """

    yield "want_write", sock


@types.coroutine
def _join(task, silent=False):
    """'Tells' the scheduler that the desired task MUST be awaited for completion
        If silent is True, any exception in the child task will be discarded

        :param task: The task to join
        :type task: class: Task
        :param silent: If ``True``, any exception raised from the child will be ignored (not recommended), defaults to ``False``
        :type silent: bool, optional
    """

    task.joined = True
    yield "want_join", task
    return task.get_result(silent)


@types.coroutine
def _cancel(task):
    """'Tells' the scheduler that the passed task must be cancelled

       The concept of cancellation here is tricky, because there is no real way to 'stop' a
       running task if not by raising an exception inside it and just ignore whatever the task
       returns (and also hoping that the task won't cause damage when exiting abruptly).
       It is highly recommended that when you write a coroutine you take into account that it might
       be cancelled at any time
    """

    task.cancelled = True
    yield "want_cancel", task
