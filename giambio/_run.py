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

from ._core import AsyncScheduler
from types import coroutine
from threading import current_thread
from time import monotonic
from hashlib import sha256


def run(coro: coroutine):
    """Shorthand for giambio.AsyncScheduler().start(coro)"""

    thread = current_thread()
    token = str(time.monotonic())
    token += thread.name
    token += str(thread.native_id)
    token += str(thread.ident)
    token = sha256(
        token.encode()
    ).hexdigest()  # Unique token specific to a given thread at a given time
