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

class GiambioError(Exception):
    """Base class for gaimbio exceptions"""
    pass


class AlreadyJoinedError(GiambioError):
    pass


class CancelledError(BaseException):
    """Exception raised as a result of the giambio.core.cancel() method"""

    def __repr__(self):
        return "giambio.exceptions.CancelledError"


class ResourceBusy(GiambioError):
    """Exception that is raised when a resource is accessed by more than
       one task at a time"""
    pass


class BrokenPipeError(GiambioError):
    """Wrapper around the broken pipe socket.error"""
    pass


class ResourceClosed(GiambioError):
    """Raised when I/O is attempted on a closed fd"""
    pass
