"""
Exceptions for giambio

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
    """
    Base class for giambio exceptions
    """

    ...


class InternalError(GiambioError):
    """
    Internal exception
    """

    ...


class CancelledError(BaseException):
    """
    Exception raised by the giambio.objects.Task.cancel() method
    to terminate a child task. This should NOT be catched, or
    at least it should be re-raised and never ignored
    """

    ...


class ResourceBusy(GiambioError):
    """
    Exception that is raised when a resource is accessed by more than
    one task at a time
    """

    ...


class ResourceClosed(GiambioError):
    """
    Raised when I/O is attempted on a closed resource
    """

    ...
