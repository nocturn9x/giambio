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

import types
from ._traps import join, cancel


class Task:

    """A simple wrapper around a coroutine object"""

    def __init__(self, coroutine: types.coroutine):
        self.coroutine = coroutine
        self.cancelled = False   # True if the task gets cancelled
        self.exc = None
        self.result = None
        self.finished = False
        self.status = "init"

    def run(self, what=None):
        """Simple abstraction layer over the coroutines ``send`` method"""

        return self.coroutine.send(what)

    def throw(self, err: Exception):
        """Simple abstraction layer over the coroutines ``throw`` method"""

        return self.coroutine.throw(err)

    async def join(self):
        """Joins the task"""

        return await join(self)

    async def cancel(self):
        """Cancels the task"""

        await cancel(self)

    def __repr__(self):
        """Implements repr(self)"""

        return f"Task({self.coroutine}, cancelled={self.cancelled}, exc={repr(self.exc)}, result={self.result}, finished={self.finished}, status={self.status})"
