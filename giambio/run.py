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

import inspect
import threading
from .core import AsyncScheduler
from .exceptions import GiambioError
from .context import TaskManager
from timeit import default_timer
from .util.debug import BaseDebugger
from types import FunctionType


thread_local = threading.local()


def get_event_loop():
    """
    Returns the event loop associated to the current
    thread
    """

    try:
        return thread_local.loop
    except AttributeError:
        raise GiambioError("giambio is not running") from None


def new_event_loop(debugger: BaseDebugger, clock: FunctionType):
    """
    Associates a new event loop to the current thread
    and deactivates the old one. This should not be
    called explicitly unless you know what you're doing.
    If an event loop is currently set and it is running,
    a GiambioError exception is raised
    """

    try:
        loop = get_event_loop()
    except GiambioError:
        thread_local.loop = AsyncScheduler(clock, debugger)
    else:
        if not loop.done():
            raise GiambioError("cannot change event loop while running")
        else:
            loop.close()
            thread_local.loop = AsyncScheduler(clock, debugger)


def run(func: FunctionType, *args, **kwargs):
    """
    Starts the event loop from a synchronous entry point
    """

    if inspect.iscoroutine(func):
        raise GiambioError("Looks like you tried to call giambio.run(your_func(arg1, arg2, ...)), that is wrong!"
                           "\nWhat you wanna do, instead, is this: giambio.run(your_func, arg1, arg2, ...)")
    elif not isinstance(func, FunctionType):
        raise GiambioError("giambio.run() requires an async function as parameter!")
    new_event_loop(kwargs.get("debugger", None), kwargs.get("clock", default_timer))
    get_event_loop().start(func, *args)


def clock():
    """
    Returns the current clock time of the thread-local event
    loop
    """

    return get_event_loop().clock()


def create_pool():
    """
    Creates an async pool
    """

    return TaskManager(get_event_loop())
