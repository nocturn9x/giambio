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

"""Helper methods to interact with the event loop"""

import types
import socket


@types.coroutine
def sleep(seconds: int):
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

    yield "sleep", seconds


@types.coroutine
def join(task):
    """'Tells' the scheduler that the desired task MUST be awaited for completion

        :param task: The task to join
        :type task: class: Task
    """

    yield "join", task
    return task.result


@types.coroutine
def cancel(task):
    """'Tells' the scheduler that the passed task must be cancelled

       The concept of cancellation here is tricky, because there is no real way to 'stop' a
       running task if not by raising an exception inside it and just ignore whatever the task
       returns (and also hoping that the task won't cause damage when exiting abruptly).
       It is highly recommended that when you write a coroutine you take into account that it might
       be cancelled at any time
    """

    yield "cancel", task
    assert task.cancelled


@types.coroutine
def want_read(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to read from the given socket

       :param sock: The socket to perform the operation on
       :type sock: class: socket.socket
    """

    yield "want_read", sock


@types.coroutine
def want_write(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to write on the given socket

       :param sock: The socket to perform the operation on
       :type sock: class: socket.socket
    """

    yield "want_write", sock

