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
from itertools import chain
from timeit import default_timer
from giambio.context import TaskManager
from typing import List, Optional, Set, Any
from giambio.util.debug import BaseDebugger
from giambio.traps import want_read, want_write
from giambio.objects import Task, TimeQueue, DeadlinesQueue, Event
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from giambio.exceptions import (InternalError,
                                CancelledError,
                                ResourceBusy,
                                GiambioError,
                                TooSlowError
                                )

# TODO: Right now this value is pretty much arbitrary, we need some testing to choose a sensible default
IO_SKIP_LIMIT = 5


class AsyncScheduler:
    """
    A simple asynchronous scheduler implementation. Tries to mimic the threaded
    model in its simplicity, without using actual threads, but rather alternating
    across coroutines execution to let more than one thing at a time to proceed
    with its calculations. An attempt to fix the threaded model has been made
    without making the API unnecessarily complicated. A few examples are tasks
    cancellation and exception propagation.

    :param clock: A callable returning monotonically increasing values at each call,
    defaults to timeit.default_timer
    :type clock: :class: types.FunctionType
    :param debugger: A subclass of giambio.util.BaseDebugger or None if no debugging output
    is desired, defaults to None
    :type debugger: :class: giambio.util.BaseDebugger
    """

    def __init__(self, clock: types.FunctionType = default_timer, debugger: BaseDebugger = None):
        """
        Object constructor
        """

        # The debugger object. If it is none we create a dummy object that immediately returns an empty
        # lambda which in turn returns None every time we access any of its attributes to avoid lots of
        # if self.debugger clauses
        if debugger:
            assert issubclass(type(debugger),
                              BaseDebugger), "The debugger must be a subclass of giambio.util.BaseDebugger"
        self.debugger = debugger or type("DumbDebugger", (object, ), {"__getattr__": lambda *args: lambda *arg: None})()
        # Tasks that are ready to run
        self.tasks: List[Task] = []
        # Selector object to perform I/O multiplexing
        self.selector: DefaultSelector = DefaultSelector()
        # This will always point to the currently running coroutine (Task object)
        self.current_task: Optional[Task] = None
        # Monotonic clock to keep track of elapsed time reliably
        self.clock: types.FunctionType = clock
        # Tasks that are asleep
        self.paused: TimeQueue = TimeQueue(self.clock)
        # All active Event objects
        self.events: Set[Event] = set()
        # Data to send back to a trap
        self.to_send: Optional[Any] = None
        # Have we ever ran?
        self.has_ran: bool = False
        # The current pool
        self.current_pool: Optional[TaskManager] = None
        # How many times we skipped I/O checks to let a task run.
        # We limit the number of times we skip such checks to avoid
        # I/O starvation in highly concurrent systems
        self.io_skip: int = 0
        # A heap queue of deadlines to be checked
        self.deadlines: DeadlinesQueue = DeadlinesQueue()

    def done(self) -> bool:
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
                if self.current_pool and self.current_pool.timeout and not self.current_pool.timed_out:
                    # Stores deadlines for tasks (deadlines are pool-specific).
                    # The deadlines queue will internally make sure not to store
                    # a deadline for the same pool twice. This makes the timeouts
                    # model less flexible, because one can't change the timeout
                    # after it is set, but it makes the implementation easier.
                    self.deadlines.put(self.current_pool)
                # Otherwise, while there are tasks ready to run, we run them!
                while self.tasks:
                    # Sets the currently running task
                    self.current_task = self.tasks.pop(0)
                    if self.current_task.done():
                        # Since ensure_discard only checks for paused tasks,
                        # we still need to make sure we don't try to execute
                        # exited tasks that are on the running queue
                        continue
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
                    if not hasattr(self, method):
                        # If this happens, that's quite bad!
                        # This if block is meant to be triggered by other async
                        # libraries, which most likely have different trap names and behaviors
                        # compared to us. If you get this exception and you're 100% sure you're
                        # not mixing async primitives from other libraries, then it's a bug!
                        raise InternalError("Uh oh! Something very bad just happened, did"
                                            " you try to mix primitives from other async libraries?") from None

                    getattr(self, method)(*args)
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
                #  frames from the exception call stack, but for now removing at least the first one
                #  seems a sensible approach (it's us catching it so we don't care about that)
                self.current_task.exc = err
                self.current_task.exc.__traceback__ = self.current_task.exc.__traceback__.tb_next
                self.current_task.status = "crashed"
                self.debugger.on_exception_raised(self.current_task, err)
                self.join(self.current_task)
                self.ensure_discard(self.current_task)

    def do_cancel(self, task: Task):
        """
        Performs task cancellation by throwing CancelledError inside the given
        task in order to stop it from running

        :param task: The task to cancel
        :type task: :class: Task
        """

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

        while self.deadlines and self.deadlines.get_closest_deadline() <= self.clock():
            pool = self.deadlines.get()
            pool.timed_out = True
            if not self.current_task.done():
                self.current_task.throw(TooSlowError())

    def check_events(self):
        """
        Checks for ready/expired events and triggers them by
        rescheduling all the tasks that called wait() on them
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

        while self.paused and self.paused.get_closest_deadline() <= self.clock():
            # Reschedules tasks when their deadline has elapsed
            task = self.paused.get()
            slept = self.clock() - task.sleep_start
            task.sleep_start = 0.0
            self.tasks.append(task)
            self.debugger.after_sleep(task, slept)

    def get_closest_deadline(self) -> float:
        """
        Gets the closest expiration deadline (asleep tasks, timeouts)

        :return: The closest deadline according to our clock
        :rtype: float
        """

        if not self.deadlines:
            # If there are no deadlines just wait until the first task wakeup
            timeout = max(0.0, self.paused.get_closest_deadline() - self.clock())
        elif not self.paused:
            # If there are no sleeping tasks just wait until the first deadline
            timeout = max(0.0, self.deadlines.get_closest_deadline() - self.clock())
        else:
            # If there are both deadlines AND sleeping tasks scheduled, we calculate
            # the absolute closest deadline among the two sets and use that as a timeout
            clock = self.clock()
            timeout = min([max(0.0, self.paused.get_closest_deadline() - clock), self.deadlines.get_closest_deadline() - clock])
        return timeout

    def check_io(self):
        """
        Checks for I/O and implements part of the sleeping mechanism
        for the event loop
        """

        before_time = self.clock()   # Used for the debugger
        if self.tasks or self.events:
            # If there is work to do immediately we prefer to
            # do that first unless some conditions are met, see below
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
            timeout = self.get_closest_deadline()
        else:
            # If there is *only* I/O, we wait a fixed amount of time
            timeout = 86400   # Stolen from trio :D
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

        entry = Task(func.__name__ or str(func), func(*args), None)
        self.tasks.append(entry)
        self.debugger.on_start()
        self.run()
        self.has_ran = True
        self.debugger.on_exit()
        if entry.exc:
            raise entry.exc

    def cancel_pool(self, pool: TaskManager) -> bool:
        """
        Cancels all tasks in the given pool

        :param pool: The pool to be cancelled
        :type pool: :class: TaskManager
        """

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

    def get_event_tasks(self) -> Task:
        """
        Yields all tasks currently waiting on events
        """

        for evt in self.events:
            for waiter in evt.waiters:
                yield waiter

    def get_asleep_tasks(self) -> Task:
        """
        Yields all tasks that are currently sleeping
        """

        for asleep in self.paused.container:
            yield asleep[2]   # Deadline, tiebreaker, task

    def get_io_tasks(self) -> Task:
        """
        Yields all tasks currently waiting on I/O resources
        """

        if self.selector.get_map():
            for k in self.selector.get_map().values():
                yield k.data

    def get_all_tasks(self) -> chain:
        """
        Returns a generator yielding all tasks which the loop is currently
        keeping track of: this includes both running and paused tasks.
        A paused task is a task which is either waiting on an I/O resource,
        sleeping, or waiting on an event to be triggered
        """

        return chain(self.tasks,
                     self.get_asleep_tasks(),
                     self.get_event_tasks(),
                     self.get_io_tasks(),
                     [self.current_task])

    def ensure_discard(self, task: Task):
        """
        Ensures that tasks that need to be cancelled are not
        rescheduled further. This method exists because tasks might
        be cancelled in a context where it's not obvious which Task
        object must be discarded and not rescheduled at the next iteration
        """

        # TODO: Do we need else ifs or ifs? The question arises because
        #  tasks might be doing I/O and other stuff too even if not at the same time
        if task in self.paused:
            self.paused.discard(task)
        if self.selector.get_map():
            for key in dict(self.selector.get_map()).values():
                if key.data == task:
                    self.selector.unregister(key.fileobj)
        if task in self.get_event_tasks():
            for evt in self.events:
                if task in evt.waiters:
                    evt.waiters.remove(task)

    def cancel_all(self) -> bool:
        """
        Cancels ALL tasks as returned by self.get_all_tasks() and returns
        whether all tasks exited or not
        """

        for to_cancel in self.get_all_tasks():
            self.cancel(to_cancel)
        return all([t.done() for t in self.get_all_tasks()])

    def close(self, *, ensure_done: bool = True):
        """
        Closes the event loop, terminating all tasks
        inside it and tearing down any extra machinery.
        If ensure_done equals False, the loop will cancel ALL
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

    # noinspection PyMethodMayBeStatic
    def is_pool_done(self, pool: TaskManager) -> bool:
        """
        Returns true if the given pool has finished
        running and can be safely terminated

        :return: Whether the pool finished running
        :rtype:  bool
        """

        if not pool:
            # The parent task has no pool
            return True
        return pool.done()

    def join(self, task: Task):
        """
        Joins a task to its callers (implicitly, the parent
        task, but also every other task who called await
        task.join() on the task object)
        """

        task.joined = True
        if task.finished or task.cancelled:
            if self.is_pool_done(self.current_pool):
                # If the current pool has finished executing or we're at the first parent
                # task that kicked the loop, we can safely reschedule the parent(s)
                self.reschedule_joiners(task)
        elif task.exc:
            if self.cancel_pool(self.current_pool):
                # This will reschedule the parent(s)
                # only if all the tasks inside the current
                # pool have finished executing, either
                # by cancellation, an exception
                # or just returned
                for t in task.joiners:
                    # Propagate the exception
                    try:
                        t.throw(task.exc)
                    except StopIteration:
                        # TODO: Need anything else?
                        task.joiners.remove(t)
                self.reschedule_joiners(task)

    def sleep(self, seconds: int or float):
        """
        Puts the current task to sleep for a given amount of seconds
        """

        self.debugger.before_sleep(self.current_task, seconds)
        if seconds:
            self.current_task.status = "sleep"
            self.current_task.sleep_start = self.clock()
            self.paused.put(self.current_task, seconds)
            self.current_task.next_deadline = self.current_task.sleep_start + seconds
        else:
            # When we're called with a timeout of 0 (the type checking is done
            # way before this point) this method acts as a checkpoint that allows
            # giambio to kick in and to its job without pausing the task's execution
            # for too long. It is recommended to put a couple of checkpoints like these
            # in your code if you see degraded concurrent performance in parts of your code
            # that block the loop
            self.tasks.append(self.current_task)

    def cancel(self, task: Task):
        """
        Schedules the task to be cancelled later
        or does so straight away if it is safe to do so
        """

        if task.done():
            self.ensure_discard(task)
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
                # it for the next execution step of the task. Giambio will also make sure
                # to re-raise cancellations at every checkpoint until the task lets the
                # exception propagate into us, because we *really* want the task to be
                # cancelled
                task.status = "cancelled"
                task.cancelled = True
                task.cancel_pending = False
                self.debugger.after_cancel(task)
                self.ensure_discard(task)
        else:
            # If we can't cancel in a somewhat "graceful" way, we just
            # defer this operation for later (check run() for more info)
            task.cancel_pending = True  # Cancellation is deferred

    def event_set(self, event: Event):
        """
        Sets an event

        :param event: The event object to trigger
        :type event: :class: Event
        """

        # When an event is set, we store the event object
        # for later, set its attribute and reschedule the
        # task that called this method. All tasks waiting
        # on this event object will be waken up on the next
        # iteration
        self.events.add(event)
        event.set = True
        self.tasks.append(self.current_task)

    def event_wait(self, event):
        """
        Pauses the current task on an event

        :param event: The event object to pause upon
        :type event: :class: Event
        """

        event.waiters.append(self.current_task)
        # Since we don't reschedule the task, it will
        # not execute until check_events is called

    def register_sock(self, sock: socket.socket, evt_type: str):
        """
        Registers the given socket inside the
        selector to perform I/0 multiplexing

        :param sock: The socket on which a read or write operation
        has to be performed
        :type sock: socket.socket
        :param evt_type: The type of event to perform on the given
        socket, either "read" or "write"
        :type evt_type: str
        """

        self.current_task.status = "io"
        evt = EVENT_READ if evt_type == "read" else EVENT_WRITE
        if self.current_task.last_io:
            # Since most of the times tasks will perform multiple
            # I/O operations on a given socket, unregistering them
            # every time isn't a sensible approach. A quick and
            # easy optimization to address this problem is to
            # store the last I/O operation that the task performed
            # together with the resource itself, inside the task
            # object. If the task wants to perform the same
            # operation on the same socket again, then this method
            # returns immediately as the socket is already being
            # watched by the selector. If the resource is the same,
            # but the event has changed, then we modify the resource's
            # associated event. Only if the resource is different from
            # the last used one this method will register a new socket
            if self.current_task.last_io == (evt_type, sock):
                # Socket is already listening for that event!
                return
            elif self.current_task.last_io[1] == sock:
                # If the event to listen for has changed we just modify it
                self.selector.modify(sock, evt, self.current_task)
                self.current_task.last_io = (evt_type, sock)
        else:
            # Otherwise we register the new socket in our selector
            self.current_task.last_io = evt_type, sock
            try:
                self.selector.register(sock, evt, self.current_task)
            except KeyError:
                # The socket is already registered doing something else
                raise ResourceBusy("The given socket is being read/written by another task") from None

    # noinspection PyMethodMayBeStatic
    async def connect_sock(self, sock: socket.socket, address_tuple: tuple):
        """
        Connects a socket asynchronously to a given endpoint

        :param sock: The socket that must to be connected
        :type sock: socket.socket
        :param address_tuple: A tuple in the same form as the one
        passed to socket.socket.connect with an address as a string
        and a port as an integer
        :type address_tuple: tuple
        """

        await want_write(sock)
        try:
            return sock.connect(address_tuple)
        except BlockingIOError:
            await want_write(sock)
            return sock.connect(address_tuple)
