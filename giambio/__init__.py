"""
Giambio: Asynchronous Python made easy (and friendly)

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

__author__ = "Nocturn9x"
__version__ = (0, 0, 1)


from . import exceptions, socket, context, core
from .socket import wrap_socket
from .traps import sleep, current_task
from .objects import Event
from .run import run, clock, create_pool, get_event_loop, new_event_loop, with_timeout
from .util import debug


__all__ = [
    "exceptions",
    "core",
    "context",
    "sleep",
    "Event",
    "run",
    "clock",
    "wrap_socket",
    "create_pool",
    "with_timeout",
    "get_event_loop",
    "current_task",
    "new_event_loop",
    "debug"
]
