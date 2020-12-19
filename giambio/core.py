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
from giambio.objects import Task, TimeQueue, DeadlinesQueue
from giambio.traps import want_read, want_write
from giambio.util.debug import BaseDebugger
from itertools import chain
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from giambio.exceptions import (InternalError,
                                CancelledError,
                                ResourceBusy,
                                GiambioError,
                                TooSlowError
                                )

# TODO: Take into account SSLWantReadError and SSLWantWriteError
IOInterrupt = (BlockingIOError, InterruptedError)
# TODO: Right now this value is pretty much arbitrary, we need some euristic testing to choose a sensible default
IO_SKIP_LIMIT = 5


class AsyncScheduler:
    """
    A simple asynchronous scheduler implementation. Tries to mimic the threaded
    model in its simplicity, without using actual threads, but rather alternating
    across coroutines execution to let more than one thing at a time to proceed
    with its calculations. An attempt to fix the threaded model has been made
    without making the API unnecessarily complicated. A few examples are tasks
    cancellation and exception propagation.
    """

    def __init__(self, clock: types.FunctionType = default_timer, debugger: BaseDebugger = None):
        """
        Object constructor
        """

        # The debugger object. If it is none we create a dummy object that immediately returns an empty
        # lambda every time you access any of its attributes to avoid lots of if self.debugger clauses
        if debugger:
            assert issubclass(type(debugger),
                              BaseDebugger), "The debugger must be a subclass of giambio.util.BaseDebugger"
        self.debugger = debugger or type("DumbDebugger", (object, ), {"__getattr__": lambda *args: lambda *arg: None})()
        # Tasks that are ready to run
        self.tasks = []
        # Selector object to perform I/O multiplexing
        self.selector = DefaultSelector()
        # This will always point to the currently running coroutine (Task object)
        self.current_task = None
        # Monotonic clock to keep track of elapsed time reliably
        self.clock = clock
        # Tasks that are asleep
        self.paused = TimeQueue(self.clock)
        # All active Event objects
        self.events = set()
        # Data to send back to a trap
        self.to_send = None
        # Have we ever ran?
        self.has_ran = False
        # The current pool
        self.current_pool = None
        # How many times we skipped I/O checks to let a task run.
        # We limit the number of times we skip such checks to avoid
        # I/O starvation in highly concurrent systems
        self.io_skip = 0
        # A heap queue of deadlines to be checked
        self.deadlines = DeadlinesQueue()

    def done(self):
        """
        Returns True if there is no work to do
        """

        if any([self.paused, self.tasks, self.events, self.selector.get_map()]):
            return False
        return True

    def shutdown(self):
        """
        Shuts down the event loop
        """

        self.selector.close()
        # TODO: Anything else?

    def run(self):
        """
        Starts the loop and 'listens' for events until there is work to do,
        then exits. This behavior kinda resembles a kernel, as coroutines can
        request the loop's functionality only trough some fixed entry points,
        which in turn yield and give execution control to the loop itself.
        """

        while True:
            try:
                if self.done():
                    # If we're done, which means there are
                    # both no paused tasks and no running tasks, we
                    # simply tear us down and return to self.start
                    self.close()
                    break
                elif not self.tasks:
                    # If there are no actively running tasks, we start by checking
                    # for I/O. This method will wait for I/O until the closest deadline
                    # to avoid starving sleeping tasks
                    if self.selector.get_map():
                        self.check_io()
                    if self.deadlines:
                        # Then we start checking for deadlines, if there are any
                        self.expire_deadlines()
                    if self.paused:
                        # Next we try to (re)schedule the asleep tasks
                        self.awake_sleeping()
                    # Then we try to awake event-waiting tasks
                    if self.events:
                        self.check_events()
                # Otherwise, while there are tasks ready to run, we run them!
                while self.tasks:
                    # Sets the currently running task
                    self.current_task = self.tasks.pop(0)
                    # Sets the current pool (for nested pools)
                    self.current_pool = self.current_task.pool
                    if self.current_pool and self.current_pool.timeout and not self.current_pool.timed_out:
                        # Stores deadlines for tasks (deadlines are pool-specific).
                        # The deadlines queue will internally make sure not to store
                        # a deadline for the same pool twice. This makes the timeouts
                        # model less flexible, because one can't change the timeout
                        # after it is set, but it makes the implementation easier.
                        self.deadlines.put(self.current_pool.timeout, self.current_pool)
                    self.debugger.before_task_step(self.current_task)
                    if self.current_task.cancel_pending:
                        # We perform the deferred cancellation
                        # if it was previously scheduled
                        self.cancel(self.current_task)
                    if self.to_send and self.current_task.status != "init":
                        # A little setup to send objects from and to
                        # coroutines outside the event loop
                        data = self.to_send
                    else:
                        # The first time coroutines' method .send() wants None!
                        data = None
                    # Run a single step with the calculation (i.e. until a yield
                    # somewhere)
                    method, *args = self.current_task.run(data)
                    # Some debugging and internal chatter here
                    self.current_task.status = "run"
                    self.current_task.steps += 1
                    self.debugger.after_task_step(self.current_task)
                    # If data has been sent, reset it to None
                    if self.to_send and self.current_task != "init":
                        self.to_send = None
                    # Sneaky method call, thanks to David Beazley for this ;)
                    getattr(self, method)(*args)
            except AttributeError:  # If this happens, that's quite bad!
                # This exception block is meant to be triggered by other async
                # libraries, which most likely have different trap names and behaviors
                # compared to us. If you get this exception and you're 100% sure you're
                # not mixing async primitives from other libraries, then it's a bug!
                raise InternalError("Uh oh! Something very bad just happened, did"
                                    " you try to mix primitives from other async libraries?") from None
            except StopIteration as ret:
                # At the end of the day, coroutines are generator functions with
                # some tricky behaviors, and this is one of them. When a coroutine
                # hits a return statement (either explicit or implicit), it raises
                # a StopIteration exception, which has an attribute named value that
                # represents the return value of the coroutine, if any. Of course this
                # exception is not an error and we should happily keep going after it,
                # most of this code below is just useful for internal/debugging purposes
                self.current_task.status = "end"
                self.current_task.result = ret.value
                self.current_task.finished = True
                self.debugger.on_task_exit(self.current_task)
                self.join(self.current_task)
            except BaseException as err:
                # TODO: We might want to do a bit more complex traceback hacking to remove any extra
                # frames from the exception call stack, but for now removing at least the first one
                # seems a sensible approach (it's us catching it so we don't care about that)
                self.current_task.exc = err
                self.current_task.exc.__traceback__ = self.current_task.exc.__traceback__.tb_next
                self.current_task.status = "crashed"
                self.debugger.on_exception_raised(self.current_task, err)
                self.join(self.current_task)

    def do_cancel(self, task: Task):
        """
        Performs task cancellation by throwing CancelledError inside the given
        task in order to stop it from running. The loop continues to execute
        as tasks are independent
        """

        if not task.cancelled and not task.exc:
            self.debugger.before_cancel(task)
            task.throw(CancelledError())

    def get_current(self):
        """
        Returns the current task to an async caller
        """

        self.tasks.append(self.current_task)
        self.to_send = self.current_task

    def expire_deadlines(self):
        """
        Handles expiring deadlines by raising an exception
        inside the correct pool if its timeout expired
        """

        while self.deadlines and self.deadlines[0][0] <= self.clock():
            _, __, pool = self.deadlines.get()
            pool.timed_out = True
            self.current_task.throw(TooSlowError())

    def check_events(self):
        """
        Checks for ready or expired events and triggers them
        """

        for event in self.events.copy():
            if event.set:
                # When an event is set, all the tasks
                # that called wait() on it are waken up.
                # Since events can only be triggered once,
                # we discard the event object from our
                # set after we've rescheduled its waiters.
                event.event_caught = True
                self.tasks.extend(event.waiters)
                self.events.remove(event)

    def awake_sleeping(self):
        """
        Reschedules sleeping tasks if their deadline
        has elapsed
        """

        while self.paused and self.paused[0][0] <= self.clock():
            # Reschedules tasks when their deadline has elapsed
            task = self.paused.get()
            if not task.done():
                slept = self.clock() - task.sleep_start
                task.sleep_start = 0.0
                self.tasks.append(task)
                self.debugger.after_sleep(task, slept)

    def check_io(self):
        """
        Checks for I/O and implements the sleeping mechanism
        for the event loop
        """

        before_time = self.clock()   # Used for the debugger
        if self.tasks or self.events:
            self.io_skip += 1
            if self.io_skip == IO_SKIP_LIMIT:
                # We can't skip every time there's some task ready
                # or else we might starve I/O waiting tasks
                # when a lot of things are running at the same time
                self.io_skip = 0
                timeout = 86400
            else:
                # If there are either tasks or events and no I/O, don't wait
                # (unless we already skipped this check too many times)
                timeout = 0.0
        elif self.paused or self.deadlines:
            # If there are asleep tasks or deadlines, wait until the closest date
            if not self.deadlines:
                # If there are no deadlines just wait until the first task wakeup
                timeout = min([max(0.0, self.paused[0][0] - self.clock())])
            elif not self.paused:
                # If there are no sleeping tasks just wait until the first deadline
                timeout = min([max(0.0, self.deadlines[0][0] - self.clock())])
            else:
                # If there are both deadlines AND sleeping tasks scheduled we calculate
                # the absolute closest deadline among the two sets and use that as a timeout
                clock = self.clock()
                timeout = min([max(0.0, self.paused[0][0] - clock), self.deadlines[0][0] - clock])
        else:
            # If there is *only* I/O, we wait a fixed amount of time
            timeout = 86400   # Thanks trio :D
        self.debugger.before_io(timeout)
        io_ready = self.selector.select(timeout)
        # Get sockets that are ready and schedule their tasks
        for key, _ in io_ready:
            self.tasks.append(key.data)  # Resource ready? Schedule its task
        self.debugger.after_io(self.clock() - before_time)

    def start(self, func: types.FunctionType, *args):
        """
        Starts the event loop from a sync context
        """

        entry = Task(func(*args), func.__name__ or str(func), None)
        self.tasks.append(entry)
        self.debugger.on_start()
        self.run()
        self.has_ran = True
        self.debugger.on_exit()
        if entry.exc:
            raise entry.exc

    def reschedule_joiners(self, task: Task):
        """
        Reschedules the parent(s) of the
        given task, if any
        """

        for t in task.joiners:
            if t not in self.tasks:
                # Since a task can be the parent
                # of multiple children, we need to
                # make sure we reschedule it only
                # once, otherwise a RuntimeError will
                # occur
                self.tasks.append(t)

    def get_event_tasks(self):
        """
        Returns all tasks currently waiting on events
        """

        return set(waiter for waiter in (evt.waiters for evt in self.events))

    def cancel_all_from_current_pool(self, pool=None):
        """
        Cancels all tasks in the current pool (or the given one)
        """

        pool = pool or self.current_pool
        if pool:
            for to_cancel in pool.tasks:
                self.cancel(to_cancel)
            # If pool.done() equals True, then self.join() can
            # safely proceed and reschedule the parent of the
            # current pool. If, however, there are still some
            # tasks running, we wait for them to exit in order
            # to avoid orphaned tasks
            return pool.done()
        else:   # If we're at the main task, we're sure everything else exited
            return True

    def get_io_tasks(self):
        """
        Return all tasks waiting on I/O resources
        """

        return [k.data for k in self.selector.get_map().values()]

    def get_all_tasks(self):
        """
        Returns all tasks which the loop is currently keeping track of.
        This includes both running and paused tasks. A paused task is a
        task which is either waiting on an I/O resource, sleeping, or
        waiting on an event to be triggered
        """

        return chain(self.tasks, self.paused, self.get_event_tasks(), self.get_io_tasks())

    def cancel_all(self):
        """
        Cancels ALL tasks, this method is called as a result
        of self.close()
        """

        for to_cancel in self.get_all_tasks():
            self.cancel(to_cancel)
        return all([t.done() for t in self.get_all_tasks()])

    def close(self, *, ensure_done: bool = True):
        """
        Closes the event loop, terminating all tasks
        inside it and tearing down any extra machinery.
        If ensure_done equals False, the loop will cancel *ALL*
        running and scheduled tasks and then tear itself down.
        If ensure_done equals True, which is the default behavior,
        this method will raise a GiambioError if the loop hasn't
        finished running.
        """

        if ensure_done:
            self.cancel_all()
        elif not self.done():
            raise GiambioError("event loop not terminated, call this method with ensure_done=False to forcefully exit")
        self.shutdown()

    def join(self, task: Task):
        """
        Joins a task to its callers (implicitly, the parent
        task, but also every other task who called await
        task.join() on the task object)
        """

        task.joined = True
        if task.finished or task.cancelled:
            if self.current_pool and self.current_pool.done() or not self.current_pool:
                self.reschedule_joiners(task)
        elif task.exc:
            if self.cancel_all_from_current_pool():
                # This will reschedule the parent
                # only if all the tasks inside it
                # have finished executing, either
                # by cancellation, an exception
                # or just returned
                self.reschedule_joiners(task)

    def sleep(self, seconds: int or float):
        """
        Puts the caller to sleep for a given amount of seconds
        """

        self.debugger.before_sleep(self.current_task, seconds)
        if seconds:   # if seconds == 0, this acts as a switch!
            self.current_task.status = "sleep"
            self.current_task.sleep_start = self.clock()
            self.paused.put(self.current_task, seconds)
            self.current_task.next_deadline = self.current_task.sleep_start + seconds
        else:
            self.tasks.append(self.current_task)

    def cancel(self, task: Task):
        """
        Schedules the task to be cancelled later
        or does so straight away if it is safe to do so
        """

        if task.done():
            # The task isn't running already!
            return
        elif task.status in ("io", "sleep", "init"):
            # We cancel immediately only in a context where it's safer to do
            # so. The concept of "safer" is quite tricky, because even though the
            # task is technically not running, it might leave some unfinished state
            # or dangling resource open after being cancelled, so maybe we need
            # a different approach altogether
            try:
                self.do_cancel(task)
            except CancelledError:
                # When a task needs to be cancelled, giambio tries to do it gracefully
                # first: if the task is paused in either I/O or sleeping, that's perfect.
                # But we also need to cancel a task if it was not sleeping or waiting on
                # any I/O because it could never do so (therefore blocking everything
                # forever). So, when cancellation can't be done right away, we schedule
                # if for the next execution step of the task. Giambio will also make sure
                # to re-raise cancellations at every checkpoint until the task lets the
                # exception propagate into us, because we *really* want the task to be
                # cancelled, and since asking kindly didn't work we have to use some
                # force :)
                task.status = "cancelled"
                task.cancelled = True
                task.cancel_pending = False
                self.debugger.after_cancel(task)
                self.paused.discard(task)
        else:
            # If we can't cancel in a somewhat "graceful" way, we just
            # defer this operation for later (check run() for more info)
            task.cancel_pending = True  # Cancellation is deferred

    def event_set(self, event):
        """
        Sets an event
        """

        self.events.add(event)
        event.set = True
        self.tasks.append(self.current_task)

    def event_wait(self, event):
        """
        Pauses the current task on an event
        """

        event.waiters.append(self.current_task)
        # Since we don't reschedule the task, it will
        # not execute until check_events is called

    # TODO: More generic I/O rather than just sockets (threads)
    def read_or_write(self, sock: socket.socket, evt_type: str):
        """
        Registers the given socket inside the
        selector to perform I/0 multiplexing
        """

        self.current_task.status = "io"
        if self.current_task.last_io:
            if self.current_task.last_io == (evt_type, sock):
                # Socket is already scheduled!
                return
            # TODO: Inspect why modify() causes issues
            self.selector.unregister(sock)
        self.current_task.last_io = evt_type, sock
        evt = EVENT_READ if evt_type == "read" else EVENT_WRITE
        try:
            self.selector.register(sock, evt, self.current_task)
        except KeyError:
            # The socket is already registered doing something else
            raise ResourceBusy("The given resource is busy!") from None

    # noinspection PyMethodMayBeStatic
    async def read_sock(self, sock: socket.socket, buffer: int):
        """
        Reads from a socket asynchronously, waiting until the resource is
        available and returning up to buffer bytes from the socket
        """

        await want_read(sock)
        return sock.recv(buffer)

    # noinspection PyMethodMayBeStatic
    async def accept_sock(self, sock: socket.socket):
        """
        Accepts a socket connection asynchronously, waiting until the resource
        is available and returning the result of the sock.accept() call
        """

        # TODO: Is this ok?
        # This does not feel right because the loop will only
        # exit when the socket has been accepted, preventing other
        # stuff from running
        while True:
            try:
                return sock.accept()
            except IOInterrupt:    # Do we need this exception thingy everywhere?
                # Some methods have never errored out, but this did and doing
                # so seemed to fix the issue, needs investigation
                await want_read(sock)

    # noinspection PyMethodMayBeStatic
    async def sock_sendall(self, sock: socket.socket, data: bytes):
        """
        Sends all the passed bytes trough a socket asynchronously
        """

        while data:
            await want_write(sock)
            sent_no = sock.send(data)
            data = data[sent_no:]

    # TODO: This method seems to cause issues
    async def close_sock(self, sock: socket.socket):
        """
        Closes a socket asynchronously
        """

        await want_write(sock)
        sock.close()
        self.selector.unregister(sock)
        self.current_task.last_io = ()

    # noinspection PyMethodMayBeStatic
    async def connect_sock(self, sock: socket.socket, addr: tuple):
        """
        Connects a socket asynchronously
        """

        await want_write(sock)
        return sock.connect(addr)
