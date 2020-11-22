"""
The main runtime environment for giambio

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
import socket
from time import sleep as wait
from timeit import default_timer
from .objects import Task, TimeQueue
from socket import SOL_SOCKET, SO_ERROR
from .traps import want_read, want_write
from .util.debug import BaseDebugger
from collections import deque
from itertools import chain
from .socket import AsyncSocket, WantWrite, WantRead
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from .exceptions import (InternalError,
                         CancelledError,
                         ResourceBusy,
                         )



class AsyncScheduler:
    """
    An asynchronous scheduler implementation. Tries to mimic the threaded
    model in its simplicity, without using actual threads, but rather alternating
    across coroutines execution to let more than one thing at a time to proceed
    with its calculations. An attempt to fix the threaded model has been made
    without making the API unnecessarily complicated.
    A few examples are tasks cancellation and exception propagation.
    """

    def __init__(self, debugger: BaseDebugger = None):
        """
        Object constructor
        """

        # The debugger object. If it is none we create a dummy object that immediately returns an empty
        # lambda every time you access any of its attributes to avoid lots of if self.debugger clauses
        if debugger:
            assert issubclass(type(debugger), BaseDebugger), "The debugger must be a subclass of giambio.util.BaseDebugger"
        self.debugger = debugger or type("DumbDebugger", (object, ), {"__getattr__": lambda *args: lambda *args: None})()
        # Tasks that are ready to run
        self.tasks = []
        # Selector object to perform I/O multiplexing
        self.selector = DefaultSelector()
        # This will always point to the currently running coroutine (Task object)
        self.current_task = None
        # Monotonic clock to keep track of elapsed time reliably
        self.clock = default_timer
        # Tasks that are asleep
        self.paused = TimeQueue(self.clock)
        # All active Event objects
        self.events = set()
        # Data to send back to a trap
        self.to_send = None
        # Have we ever ran?
        self.has_ran = False

    def done(self):
        """
        Returns True if there is work to do
        """

        if any([self.paused, self.tasks, self.events, self.selector.get_map()]):
            return False
        return True

    def shutdown(self):
        """
        Shuts down the event loop
        """

        # TODO: See if other teardown is required (massive join()?)
        self.selector.close()

    def run(self):
        """
        Starts the loop and 'listens' for events until there is work to do,
        then exits. This behavior kinda reflects a kernel, as coroutines can
        request the loop's functionality only trough some fixed entry points,
        which in turn yield and give execution control to the loop itself.
        """

        while True:
            try:
                if self.done():
                    # If we're done, which means there is no 
                    # sleeping tasks, no events to deliver,
                    # no I/O to do and no running tasks, we
                    # simply tear us down and return to self.start
                    self.shutdown()
                    break
                elif not self.tasks:
                    # If there are no actively running tasks
                    # we try to schedule the asleep ones
                    self.awake_sleeping()
                    # The next step is checking for I/O
                    self.check_io()
                    # Try to awake event-waiting tasks
                    self.check_events()
                # Otherwise, while there are tasks ready to run, well, run them!
                while self.tasks:
                    # Sets the currently running task
                    self.current_task = self.tasks.pop(0)
                    self.debugger.before_task_step(self.current_task)
                    if self.current_task.cancel_pending:
                        self.do_cancel()
                    if self.to_send and self.current_task.status != "init":
                        data = self.to_send
                    else:
                        data = None
                    # Run a single step with the calculation
                    method, *args = self.current_task.run(data)
                    self.current_task.status = "run"
                    self.current_task.steps += 1
                    self.debugger.after_task_step(self.current_task)
                    # Data has been sent, reset it to None
                    if self.to_send and self.current_task != "init":
                        self.to_send = None
                    # Sneaky method call, thanks to David Beazley for this ;)
                    getattr(self, method)(*args)
            except AttributeError:  # If this happens, that's quite bad!
                raise InternalError("Uh oh! Something very bad just happened, did"
            " you try to mix primitives from other async libraries?") from None
            except CancelledError:
                self.current_task.status = "cancelled"
                self.current_task.cancelled = True
                self.current_task.cancel_pending = False
                self.debugger.after_cancel(self.current_task)
                self.join(self.current_task)   # TODO: Investigate if a call to join() is needed
            except StopIteration as ret:
                # Coroutine ends
                self.current_task.status = "end"
                self.current_task.result = ret.value
                self.current_task.finished = True
                self.debugger.on_task_exit(self.current_task)
                self.join(self.current_task)
            except BaseException as err:
                self.current_task.exc = err
                self.current_task.status = "crashed"
                self.join(self.current_task)

    def do_cancel(self, task: Task = None):
        """
        Performs task cancellation by throwing CancelledError inside the current
        task in order to stop it from executing. The loop continues to execute
        as tasks are independent
        """

        task = task or self.current_task
        self.debugger.before_cancel(task)
        task.throw(CancelledError)

    def get_running(self):
        """
        Returns the current task to an async caller
        """

        self.tasks.append(self.current_task)
        self.to_send = self.current_task

    def check_events(self):
        """
        Checks for ready or expired events and triggers them
        """

        for event in self.events.copy():
            if event.set:
                event.event_caught = True
                event.waiters.append(self.current_task)
                self.tasks.extend(event.waiters)
                self.events.remove(event)

    def awake_sleeping(self):
        """
        Checks for and reschedules sleeping tasks
        """

        wait(max(0.0, self.paused[0][0] - self.clock()))
        # Sleep until the closest deadline in order not to waste CPU cycles
        while self.paused[0][0] < self.clock():
            # Reschedules tasks when their deadline has elapsed
            task = self.paused.get()
            slept = self.clock() - task.sleep_start
            task.sleep_start = None
            self.tasks.append(task)
            self.debugger.after_sleep(task, slept)
            if not self.paused:
                break

    def check_io(self):
        """
        Checks and schedules task to perform I/O
        """

        before_time = self.clock()
        if self.tasks or self.events and not self.selector.get_map():
            # If there are either tasks or events and no I/O, never wait
            timeout = 0.0
        elif self.paused:
            # If there are asleep tasks, wait until the closest deadline
            timeout = max(0.0, self.paused[0][0] - self.clock())
        elif self.selector.get_map():
            # If there is *only* I/O, we wait a fixed amount of time
            timeout = 1  # TODO: Is this ok?
        self.debugger.before_io(timeout)
        if self.selector.get_map():
            io_ready = self.selector.select(timeout)
            # Get sockets that are ready and schedule their tasks
            for key, _ in io_ready:
                self.tasks.append(key.data)  # Resource ready? Schedule its task
        self.debugger.after_io(self.clock() - before_time)

    def start(self, func: types.FunctionType, *args):
        """
        Starts the event loop from a sync context
        """

        entry = Task(func(*args), func.__name__ or str(func))
        self.tasks.append(entry)
        self.debugger.on_start()
        self.run()
        self.has_ran = True
        self.debugger.on_exit()

    def reschedule_joinee(self, task: Task):
        """
        Reschedules the joinee of the
        given task, if any
        """

        if task.parent:
            self.tasks.append(task.parent)

    def join(self, child: Task):
        """
        Handler for the 'join' event, does some magic to tell the scheduler
        to wait until the current coroutine ends
        """

        child.joined = True
        if child.finished:
            self.reschedule_joinee(child)
        elif child.exc:
            for task in chain(self.tasks, self.paused):
                try:
                    self.cancel(task)
                except CancelledError:
                    task.status = "cancelled"
                    task.cancelled = True
                    task.cancel_pending = False
                    self.debugger.after_cancel(task)
                    self.tasks.remove(task)
            child.parent.throw(child.exc)
            self.tasks.append(child.parent)

    def sleep(self, seconds: int or float):
        """
        Puts the caller to sleep for a given amount of seconds
        """

        self.debugger.before_sleep(self.current_task, seconds)
        if seconds:
            self.current_task.status = "sleep"
            self.current_task.sleep_start = self.clock()
            self.paused.put(self.current_task, seconds)
        else:
            self.tasks.append(self.current_task)

    def cancel(self, task: Task = None):
        """
        Handler for the 'cancel' event, schedules the task to be cancelled later
        or does so straight away if it is safe to do so
        """

        task = task or self.current_task
        if not task.finished and not task.exc:
            if task.status in ("I/O", "sleep"):
                # We cancel right away
                self.do_cancel(task)
            else:
                task.cancel_pending = True  # Cancellation is deferred

    def event_set(self, event):
        """
        Sets an event
        """

        self.events.add(event)
        event.waiters.append(self.current_task)
        event.set = True
        self.reschedule_joinee()

    def event_wait(self, event):
        """
        Pauses the current task on an event
        """

        event.waiters.append(self.current_task)

    # TODO: More generic I/O rather than just sockets
    def want_read(self, sock: socket.socket):
        """
        Handler for the 'want_read' event, registers the socket inside the
        selector to perform I/0 multiplexing
        """

        self.current_task.status = "I/O"
        if self.current_task.last_io:
            if self.current_task.last_io == ("READ", sock):
                # Socket is already scheduled!
                return
            self.selector.unregister(sock)
        self.current_task.last_io = "READ", sock
        try:
            self.selector.register(sock, EVENT_READ, self.current_task)
        except KeyError:
            # The socket is already registered doing something else
            raise ResourceBusy("The given resource is busy!") from None

    def want_write(self, sock: socket.socket):
        """
        Handler for the 'want_write' event, registers the socket inside the
        selector to perform I/0 multiplexing
        """

        self.current_task.status = "I/O"
        if self.current_task.last_io:
            if self.current_task.last_io == ("WRITE", sock):
                # Socket is already scheduled!
                return
            # TODO: Inspect why modify() causes issues
            self.selector.unregister(sock)
        self.current_task.last_io = "WRITE", sock
        try:
            self.selector.register(sock, EVENT_WRITE, self.current_task)
        except KeyError:
            raise ResourceBusy("The given resource is busy!") from None
    def wrap_socket(self, sock):
        """
        Wraps a standard socket into an AsyncSocket object
        """

        return AsyncSocket(sock, self)

    async def read_sock(self, sock: socket.socket, buffer: int):
        """
        Reads from a socket asynchronously, waiting until the resource is
        available and returning up to buffer bytes from the socket
        """

        try:
            return sock.recv(buffer)
        except WantRead:
            await want_read(sock)
        return sock.recv(buffer)

    async def accept_sock(self, sock: socket.socket):
        """
        Accepts a socket connection asynchronously, waiting until the resource
        is available and returning the result of the accept() call
        """

        try:
            return sock.accept()
        except WantRead:
            await want_read(sock)
            return sock.accept()

    async def sock_sendall(self, sock: socket.socket, data: bytes):
        """
        Sends all the passed data, as bytes, trough the socket asynchronously
        """

        while data:
            try:
                sent_no = sock.send(data)
            except WantWrite:
                await want_write(sock)
                sent_no = sock.send(data)
            data = data[sent_no:]

    async def close_sock(self, sock: socket.socket):
        """
        Closes the socket asynchronously
        """

        await want_write(sock)
        self.selector.unregister(sock)
        return sock.close()

    async def connect_sock(self, sock: socket.socket, addr: tuple):
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
