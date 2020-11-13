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

import threading
from ._core import AsyncScheduler
from ._layers import Task
from .socket import AsyncSocket
from types import FunctionType, CoroutineType, GeneratorType
import socket


thread_local = threading.local()


def run(func: FunctionType, *args) -> Task:
    """
    Starts the event loop from a synchronous entry point
    """

    if isinstance(func, (CoroutineType, GeneratorType)):
        raise RuntimeError("Looks like you tried to call giambio.run(your_func(arg1, arg2, ...)), that is wrong!"
                           "\nWhat you wanna do, instead, is this: giambio.run(your_func, arg1, arg2, ...)")
    if not hasattr(thread_local, "loop"):
        thread_local.loop = AsyncScheduler()
    return thread_local.loop.start(func, *args)


def clock():
    """
    Returns the current clock time of the thread-local event
    loop
    """

    return thread_local.loop.clock()


def spawn(func: FunctionType, *args):
    """
    Spawns a child task in the current event
    loop
    """

    if isinstance(func, (CoroutineType, GeneratorType)):
        raise RuntimeError("Looks like you tried to call giambio.spawn(your_func(arg1, arg2, ...)), that is wrong!"
                           "\nWhat you wanna do, instead, is this: giambio.spawn(your_func, arg1, arg2, ...)")
    try:
        return thread_local.loop.spawn(func, *args)
    except AttributeError:
        raise RuntimeError("It appears that giambio is not running, did you call giambio.spawn(...)"
                           " outside of an async context?") from None


def wrap_socket(sock: socket.socket) -> AsyncSocket:
    """
    Wraps a synchronous socket into a giambio.socket.AsyncSocket
    """

    return thread_local.loop.wrap_socket(sock)
