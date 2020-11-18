"""
Helper methods and public API

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

import socket
import threading
from .core import AsyncScheduler
from .exceptions import GiambioError
from .context import TaskManager
from .socket import AsyncSocket
from .util.debug import BaseDebugger
from types import FunctionType, CoroutineType, GeneratorType


thread_local = threading.local()


def get_event_loop():
    """
    Returns the event loop associated to the current
    thread
    """

    try:
        return thread_local.loop
    except AttributeError:
        raise GiambioError("no event loop set") from None


def new_event_loop(debugger: BaseDebugger):
    """
    Associates a new event loop to the current thread
    and deactivates the old one. This should not be
    called explicitly unless you know what you're doing
    """

    try:
        loop = thread_local.loop
    except AttributeError:
        thread_local.loop = AsyncScheduler(debugger)
    else:
        if not loop.done():
            raise GiambioError("cannot set event loop while running")
        else:
            thread_local.loop = AsyncScheduler(debugger)


def run(func: FunctionType, *args, **kwargs):
    """
    Starts the event loop from a synchronous entry point
    """

    if isinstance(func, (CoroutineType, GeneratorType)):
        raise GiambioError("Looks like you tried to call giambio.run(your_func(arg1, arg2, ...)), that is wrong!"
                           "\nWhat you wanna do, instead, is this: giambio.run(your_func, arg1, arg2, ...)")
    elif not isinstance(func, FunctionType):
        raise GiambioError("gaibmio.run() requires an async function as parameter!")
    new_event_loop(kwargs.get("debugger", None))
    thread_local.loop.start(func, *args)


def clock():
    """
    Returns the current clock time of the thread-local event
    loop
    """

    try:
        return thread_local.loop.clock()
    except AttributeError:
        raise GiambioError("Cannot call clock from outside an async context") from None


def wrap_socket(sock: socket.socket) -> AsyncSocket:
    """
    Wraps a synchronous socket into a giambio.socket.AsyncSocket
    """
    try:
        return thread_local.loop.wrap_socket(sock)
    except AttributeError:
        raise GiambioError("Cannot wrap a socket from outside an async context") from None


def create_pool():
    """
    Creates an async pool
    """

    try:
        return TaskManager(thread_local.loop)
    except AttributeError:
        raise GiambioError("It appears that giambio is not running, did you call giambio.create_pool()"
                           " outside of an async context?") from None
