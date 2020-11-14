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

# Import libraries and internal resources
import types
from collections import defaultdict
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
import socket
from .exceptions import AlreadyJoinedError, CancelledError, ResourceBusy, GiambioError
from timeit import default_timer
from time import sleep as wait
from .socket import AsyncSocket, WantWrite, WantRead
from ._layers import Task, TimeQueue
from socket import SOL_SOCKET, SO_ERROR
from ._traps import want_read, want_write
import traceback, sys


class AsyncScheduler:
    """
    An asynchronous scheduler toy implementation. Tries to mimic the threaded
    model in its simplicity, without using actual threads, but rather alternating
    across coroutines execution to let more than one thing at a time to proceed
    with its calculations. An attempt to fix the threaded model underlying pitfalls
    and weaknesses has been made, without making the API unnecessarily complicated.
    A few examples are tasks cancellation and exception propagation.
    Can perform (unreliably) socket I/O asynchronously.
    """

    def __init__(self):
        """Object constructor"""

        self.tasks = []  # Tasks that are ready to run
        self.selector = DefaultSelector()  # Selector object to perform I/O multiplexing
        self.current_task = None  # This will always point to the currently running coroutine (Task object)
        self.joined = (
            {}
        )  # Maps child tasks that need to be joined their respective parent task
        self.clock = (
            default_timer  # Monotonic clock to keep track of elapsed time reliably
        )
        self.some_cancel = False
        self.paused = TimeQueue(self.clock)  # Tasks that are asleep
        self.events = set()  # All Event objects
        self.event_waiting = defaultdict(list)  # Coroutines waiting on event objects
        self.sequence = 0

    def _run(self):
        """
        Starts the loop and 'listens' for events until there are either ready or asleep tasks,
        then exit. This behavior kinda reflects a kernel, as coroutines can request
        the loop's functionality only trough some fixed entry points, which in turn yield and
        give execution control to the loop itself.
        """

        while True:
            try:
                if not self.selector.get_map() and not any(
                    [self.paused, self.tasks, self.event_waiting]
                ):  # If there is nothing to do, just exit
                    break
                elif not self.tasks:
                    if self.paused:
                        # If there are no actively running tasks, we try to schedule the asleep ones
                        self._check_sleeping()
                    if self.selector.get_map():
                        self._check_io()    # The next step is checking for I/O
                    if self.event_waiting:
                        # Try to awake event-waiting tasks
                        self._check_events()
                while self.tasks:  # While there are tasks to run
                    self.current_task = self.tasks.pop(0)
                    if self.some_cancel:
                        self._check_cancel()
                    # Sets the currently running task
                    method, *args = self.current_task.run()  # Run a single step with the calculation
                    self.current_task.status = "run"
                    getattr(self, f"_{method}")(*args)
                    # Sneaky method call, thanks to David Beazley for this ;)
            except CancelledError:
                self.current_task.cancelled = True
                self._reschedule_parent()
            except StopIteration as e:  # Coroutine ends
                self.current_task.result = e.args[0] if e.args else None
                self.current_task.finished = True
                self._reschedule_parent()
            except RuntimeError:
                continue
            except BaseException as error:  # Coroutine raised
                print(error)
                self.current_task.exc = error
                self._reschedule_parent()
                self._join(self.current_task)
                raise

    def _check_cancel(self):
        """
        Checks for task cancellation
        """

        if self.current_task.status == "cancel":  # Deferred cancellation
            self.current_task.cancelled = True
            self.current_task.throw(CancelledError(self.current_task))

    def _check_events(self):
        """
        Checks for ready or expired events and triggers them
        """

        for event, tasks in self.event_waiting.copy().items():
            if event._set:
                event.event_caught = True
                self.tasks.extend(tasks + [event.notifier])
                self.event_waiting.pop(event)

    def _check_sleeping(self):
        """
        Checks and reschedules sleeping tasks
        """

        wait(max(0.0, self.paused[0][0] - self.clock()))
        # Sleep until the closest deadline in order not to waste CPU cycles
        while self.paused[0][0] < self.clock():
            # Reschedules tasks when their deadline has elapsed
            self.tasks.append(self.paused.get())
            if not self.paused:
                break

    def _check_io(self):
        """
        Checks and schedules task to perform I/O
        """

        timeout = 0.0 if self.tasks else None
        # If there are no tasks ready wait indefinitely
        io_ready = self.selector.select(timeout)
        # Get sockets that are ready and schedule their tasks
        for key, _ in io_ready:
            self.tasks.append(key.data)  # Resource ready? Schedule its task

    def start(self, func: types.FunctionType, *args):
        """
        Starts the event loop from a sync context
        """

        entry = Task(func(*args))
        self.tasks.append(entry)
        self._join(entry)   # TODO -> Inspect this line, does it actually do anything useful?
        self._run()
        return entry

    def _reschedule_parent(self):
        """
        Reschedules the parent task of the
        currently running task, if any
        """

        parent = self.joined.pop(self.current_task, None)
        if parent:
            self.tasks.append(parent)
        return parent

    # TODO: More generic I/O rather than just sockets
    def _want_read(self, sock: socket.socket):
        """
        Handler for the 'want_read' event, registers the socket inside the selector to perform I/0 multiplexing
        """

        self.current_task.status = "I/O"
        if self.current_task._last_io:
            if self.current_task._last_io == ("READ", sock):
                return  # Socket is already scheduled!
            else:
                self.selector.unregister(sock)
        self.current_task._last_io = "READ", sock
        try:
            self.selector.register(sock, EVENT_READ, self.current_task)
        except KeyError:   # The socket is already registered doing something else
            raise ResourceBusy("The given resource is busy!") from None

    def _want_write(self, sock: socket.socket):
        """
        Handler for the 'want_write' event, registers the socket inside the selector to perform I/0 multiplexing
        """

        self.current_task.status = "I/O"
        if self.current_task._last_io:
            if self.current_task._last_io == ("WRITE", sock):
                return  # Socket is already scheduled!
            else:
                self.selector.unregister(sock)  # modify() causes issues
        self.current_task._last_io = "WRITE", sock
        try:
            self.selector.register(sock, EVENT_WRITE, self.current_task)
        except KeyError:
            raise ResourceBusy("The given resource is busy!") from None

    def _join(self, child: types.coroutine):
        """
        Handler for the 'join' event, does some magic to tell the scheduler
        to wait until the passed coroutine ends. The result of this call equals whatever the
        coroutine returns or, if an exception gets raised, the exception will get propagated inside the
        parent task
        """

        if child.cancelled or child.exc:  # Task was cancelled or has errored
            self._reschedule_parent()
        elif child.finished:    # Task finished running
            self.tasks.append(self.current_task)  # Task has already finished
        else:
            if child not in self.joined:
                self.joined[child] = self.current_task
            else:
                raise AlreadyJoinedError(
                    "Joining the same task multiple times is not allowed!"
                )

    def _sleep(self, seconds: int or float):
        """
        Puts the caller to sleep for a given amount of seconds
        """

        if seconds:
            self.current_task.status = "sleep"
            self.paused.put(self.current_task, seconds)
        else:
            self.tasks.append(self.current_task)

    def _event_set(self, event):
        """
        Sets an event
        """

        event.notifier = self.current_task
        event._set = True
        self.events.add(event)

    def _event_wait(self, event):
        """
        Waits for an event
        """

        if event in self.events:
            event.waiting -= 1
            if event.waiting <= 0:
                return self.events.remove(event)
            else:
                return
        else:
            self.event_waiting[event].append(self.current_task)

    def _cancel(self, task):
        """
        Handler for the 'cancel' event, throws CancelledError inside a coroutine
        in order to stop it from executing. The loop continues to execute as tasks
        are independent
        """

        if not self.some_cancel:
            self.some_cancel = True
        task.status = "cancel"  # Cancellation is deferred

    def wrap_socket(self, sock):
        """
        Wraps a standard socket into an AsyncSocket object
        """

        return AsyncSocket(sock, self)

    async def _read_sock(self, sock: socket.socket, buffer: int):
        """
        Reads from a socket asynchronously, waiting until the resource is available and returning up to buffer bytes
        from the socket
        """

        await want_read(sock)
        try:
            return sock.recv(buffer)
        except WantRead:
            await want_write(sock)
        return sock.recv(buffer)

    async def _accept_sock(self, sock: socket.socket):
        """
        Accepts a socket connection asynchronously, waiting until the resource is available and returning the
        result of the accept() call
        """

        await want_read(sock)
        return sock.accept()

    async def _sock_sendall(self, sock: socket.socket, data: bytes):
        """
        Sends all the passed data, as bytes, trough the socket asynchronously
        """

        while data:
            await want_write(sock)
            sent_no = sock.send(data)
            data = data[sent_no:]

    async def _close_sock(self, sock: socket.socket):
        """
        Closes the socket asynchronously
        """

        await want_write(sock)
        self.selector.unregister(sock)
        return sock.close()

    async def _connect_sock(self, sock: socket.socket, addr: tuple):
        """
        Connects a socket asynchronously
        """

        try:  # "Borrowed" from curio
            return sock.connect(addr)
        except WantWrite:
            await want_write(sock)
        err = sock.getsockopt(SOL_SOCKET, SO_ERROR)
        if err != 0:
            raise OSError(err, f"Connect call failed: {addr}")
