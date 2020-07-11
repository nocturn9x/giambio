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
from collections import deque, defaultdict
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
import socket
from .exceptions import AlreadyJoinedError, CancelledError, ResourceBusy, GiambioError
from timeit import default_timer
from time import sleep as wait
from .socket import AsyncSocket, WantWrite
from ._layers import Task, TimeQueue
from socket import SOL_SOCKET, SO_ERROR
from ._traps import want_read, want_write


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

        self.tasks = deque()  # Tasks that are ready to run
        self.selector = DefaultSelector()  # Selector object to perform I/O multiplexing
        self.current_task = None  # This will always point to the currently running coroutine (Task object)
        self.joined = {}  # Maps child tasks that need to be joined their respective parent task
        self.clock = default_timer  # Monotonic clock to keep track of elapsed time reliably
        self.paused = TimeQueue(self.clock)  # Tasks that are asleep
        self.events = {}   # All Event objects
        self.event_waiting = defaultdict(list)  # Coroutines waiting on event objects
        self.sequence = 0

    def run(self):
        """Starts the loop and 'listens' for events until there are either ready or asleep tasks
        then exit. This behavior kinda reflects a kernel, as coroutines can request
        the loop's functionality only trough some fixed entry points, which in turn yield and
        give execution control to the loop itself."""

        while True:
            if not self.selector.get_map() and not any([self.paused, self.tasks, self.event_waiting]):   # If there is nothing to do, just exit
                break
            if not self.tasks:
                if self.paused:  # If there are no actively running tasks, we try to schedule the asleep ones
                    try:
                        self.check_sleeping()
                    except BaseException as error:
                        self.current_task.exc = error
                        self.reschedule_parent(self.current_task)
            if self.selector.get_map():
                try:
                    self.check_io()
                except BaseException as error:
                    self.current_task.exc = error
                    self.reschedule_parent(self.current_task)
            while self.tasks:    # While there are tasks to run
                self.current_task = self.tasks.popleft()  # Sets the currently running task
                try:
                    if self.current_task.status == "cancel":  # Deferred cancellation
                        self.current_task.cancelled = True
                        self.current_task.throw(CancelledError(self.current_task))
                    method, *args = self.current_task.run(self.current_task._notify)   # Run a single step with the calculation (and awake event-waiting tasks if any)
                    self.current_task.status = "run"
                    getattr(self, method)(*args)  # Sneaky method call, thanks to David Beazley for this ;)
                    if self.event_waiting:
                        self.check_events()
                except CancelledError as cancelled:
                    self.tasks.remove(cancelled.args[0])   # Remove the dead task
                    self.tasks.append(self.current_task)
                except StopIteration as e:   # Coroutine ends
                    self.current_task.result = e.args[0] if e.args else None
                    self.current_task.finished = True
                    self.reschedule_parent(self.current_task)
                except BaseException as error:    # Coroutine raised
                    self.current_task.exc = error
                    self.reschedule_parent(self.current_task)

    def check_events(self):
        """Checks for ready or expired events and triggers them"""

        for event, tasks in self.event_waiting.copy().items():
            if event._set:
                event.event_caught = True
                for task in tasks:
                    task._notify = event._notify
                self.tasks.extend(tasks + [event.notifier])
                self.event_waiting.pop(event)

    def check_sleeping(self):
        """Checks and reschedules sleeping tasks"""

        wait(max(0.0, self.paused[0][0] - self.clock()))  # Sleep until the closest deadline in order not to waste CPU cycles
        while self.paused[0][0] < self.clock():  # Reschedules tasks when their deadline has elapsed
            self.tasks.append(self.paused.get())
            if not self.paused:
                break

    def check_io(self):
        """Checks and schedules task to perform I/O"""

        timeout = 0.0 if self.tasks else None  # If there are no tasks ready wait indefinitely
        io_ready = self.selector.select(timeout)    # Get sockets that are ready and schedule their tasks
        for key, _ in io_ready:
            self.tasks.append(key.data)  # Socket ready? Schedule the task

    def create_task(self, coro: types.coroutine):
        """Spawns a child task"""

        task = Task(coro)
        self.tasks.append(task)
        return task

    def schedule_task(self, coro: types.coroutine, n: int):
        """Schedules a task for execution after n seconds"""

        task = Task(coro)
        self.paused.put(task, n)
        return task

    def start(self, coro: types.coroutine):
        """Starts the event loop using a coroutine as an entry point.
        """

        entry = self.create_task(coro)
        crashed = False
        try:
            self.run()
        except BaseException as exc:
            entry.exc = exc
            crashed = True
        if crashed:
            raise GiambioError("Event loop crashed!") from entry.exc
        return entry

    def reschedule_parent(self, coro):
        """Reschedules the parent task"""

        parent = self.joined.pop(coro, None)
        if parent:
            self.tasks.append(parent)
        return parent

    def want_read(self, sock: socket.socket):
        """Handler for the 'want_read' event, registers the socket inside the selector to perform I/0 multiplexing"""

        self.current_task.status = "I/O"
        if self.current_task._last_io:
            if self.current_task._last_io == ("READ", sock):
                return    # Socket is already scheduled!
            else:
                self.selector.unregister(sock)
        busy = False
        self.current_task._last_io = "READ", sock
        try:
            self.selector.register(sock, EVENT_READ, self.current_task)
        except KeyError:
            busy = True
        if busy:
            raise ResourceBusy("The given resource is busy!")

    def want_write(self, sock: socket.socket):
        """Handler for the 'want_write' event, registers the socket inside the selector to perform I/0 multiplexing"""

        self.current_task.status = "I/O"
        if self.current_task._last_io:
            if self.current_task._last_io == ("WRITE", sock):
                return    # Socket is already scheduled!
            else:
                self.selector.unregister(sock)  # modify() causes issues
        busy = False
        self.current_task._last_io = "WRITE", sock
        try:
            self.selector.register(sock, EVENT_WRITE, self.current_task)
        except KeyError:
            busy = True
        if busy:
            raise ResourceBusy("The given resource is busy!")

    def join(self, child: types.coroutine):
        """Handler for the 'join' event, does some magic to tell the scheduler
        to wait until the passed coroutine ends. The result of this call equals whatever the
        coroutine returns or, if an exception gets raised, the exception will get propagated inside the
        parent task"""

        if child.cancelled:  # Task was cancelled and is therefore dead
            self.tasks.append(self.current_task)
        elif child.exc:     # Task raised an error, propagate it!
            self.reschedule_parent(child)
            raise child.exc
        elif child.finished:
            self.tasks.append(self.current_task)  # Task has already finished
        else:
            if child not in self.joined:
                self.joined[child] = self.current_task
            else:
                raise AlreadyJoinedError("Joining the same task multiple times is not allowed!")

    def sleep(self, seconds: int or float):
        """Puts the caller to sleep for a given amount of seconds"""

        if seconds:
            self.current_task.status = "sleep"
            self.paused.put(self.current_task, seconds)
        else:
            self.tasks.append(self.current_task)

    def event_set(self, event, value):
        """Sets an event"""

        event.notifier = self.current_task
        event._set = True
        event._notify = value
        self.events[event] = value

    def event_wait(self, event):
        """Waits for an event"""

        if self.events.get(event, None):
            event.waiting -= 1
            if event.waiting <= 0:
                return self.events.pop(event)
            else:
                return self.events[event]
        else:
            self.event_waiting[event].append(self.current_task)

    def cancel(self, task):
        """Handler for the 'cancel' event, throws CancelledError inside a coroutine
        in order to stop it from executing. The loop continues to execute as tasks
        are independent"""

        if task.status in ("sleep", "I/O") and not task.cancelled:  # It is safe to cancel a task while blocking
            task.cancelled = True
            task.throw(CancelledError(task))
        elif task.status == "run":
            task.status = "cancel"   # Cancellation is deferred

    def wrap_socket(self, sock):
        """Wraps a standard socket into an AsyncSocket object"""

        return AsyncSocket(sock, self)

    async def read_sock(self, sock: socket.socket, buffer: int):
        """Reads from a socket asynchronously, waiting until the resource is available and returning up to buffer bytes
        from the socket
        """

        await want_read(sock)
        return sock.recv(buffer)

    async def accept_sock(self, sock: socket.socket):
        """Accepts a socket connection asynchronously, waiting until the resource is available and returning the
        result of the accept() call
        """

        await want_read(sock)
        return sock.accept()

    async def sock_sendall(self, sock: socket.socket, data: bytes):
        """Sends all the passed data, as bytes, trough the socket asynchronously"""

        while data:
            await want_write(sock)
            sent_no = sock.send(data)
            data = data[sent_no:]

    async def close_sock(self, sock: socket.socket):
        """Closes the socket asynchronously"""

        await want_write(sock)
        return sock.close()

    async def connect_sock(self, sock: socket.socket, addr: tuple):
        """Connects a socket asynchronously"""

        try:  # "Borrowed" from curio
            return sock.connect(addr)
        except WantWrite:
            await want_write(sock)
        err = sock.getsockopt(SOL_SOCKET, SO_ERROR)
        if err != 0:
            raise OSError(err, f'Connect call failed: {addr}')
