import types
from collections import deque, defaultdict
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from heapq import heappush, heappop
import socket
from .exceptions import AlreadyJoinedError, CancelledError
import traceback
from timeit import default_timer
from time import sleep as wait
from .socket import AsyncSocket


class Task:

    """A simple wrapper around a coroutine object"""

    def __init__(self, coroutine: types.coroutine):
        self.coroutine = coroutine
        self.status = False  # Not ran yet
        self.joined = False
        self.ret_val = None # Return value is saved here
        self.exception = None  # If errored, the exception is saved here
        self.cancelled = False # When cancelled, this is True

    def run(self):
        self.status = True
        return self.coroutine.send(None)

    def __repr__(self):
        return f"giambio.core.Task({self.coroutine}, {self.status}, {self.joined}, {self.ret_val}, {self.exception}, {self.cancelled})"

    async def cancel(self):
        return await cancel(self)

    async def join(self):
        return await join(self)


class EventLoop:

    """Implementation of an event loop, alternates between execution of coroutines (asynchronous functions)
    to allow a concurrency model or 'green threads'"""

    def __init__(self):
        """Object constructor"""

        self.to_run = deque()  # Scheduled tasks
        self.paused = []  # Sleeping tasks
        self.selector = DefaultSelector()  # Selector object to perform I/O multiplexing
        self.running = None  # This will always point to the currently running coroutine (Task object)
        self.joined = defaultdict(list)  # Tasks that want to join
        self.clock = default_timer  # Monotonic clock to keep track of elapsed time

    def loop(self):
        """Main event loop for giambio"""

        while True:
            if not self.selector.get_map() and not self.to_run:
                break
            while self.selector.get_map():   # If there are sockets ready, (re)schedule their associated task
                timeout = 0.0 if self.to_run else None
                tasks = deque(self.selector.select(timeout))
                for key, _ in tasks:
                    self.to_run.append(key.data)  # Socket ready? Schedule the task
                    self.selector.unregister(key.fileobj)  # Once (re)scheduled, the task does not need to perform I/O multiplexing (for now)
            while self.to_run or self.paused:
                if not self.to_run:
                    wait(max(0.0, self.paused[0][0] - self.clock()))  # If there are no tasks ready, just do nothing
                while self.paused and self.paused[0][0] < self.clock():  # Reschedules task when their timer has elapsed
                    _, coro = heappop(self.paused)
                    self.to_run.append(coro)
                self.running = self.to_run.popleft()  # Sets the currently running task
                try:
                    method, *args = self.running.run()  # Sneaky method call, thanks to David Beazley for this ;)
                    getattr(self, method)(*args)
                except StopIteration as e:
                    self.running.ret_value = e.args[0] if e.args else None  # Saves the return value
                    self.to_run.extend(self.joined.pop(self.running, ()))  # Reschedules the parent task
                except CancelledError:
                    self.running.cancelled = True  # Update the coroutine status
                    raise
                except Exception as has_raised:
                    self.to_run.extend(self.joined.pop(self.running, ()))  # Reschedules the parent task
                    if self.running.joined:    # Let the join function handle the hassle of propagating the error
                        self.running.exception = has_raised  # Save the exception
                    else:  # Let the exception propagate (I'm looking at you asyncIO ;))
                        raise
                except KeyboardInterrupt:
                    self.running.coroutine.throw(KeyboardInterrupt)

    def spawn(self, coroutine: types.coroutine):
        """Schedules a task for execution, appending it to the call stack"""

        task = Task(coroutine)
        self.to_run.append(task)
        return task

    def start(self, coroutine: types.coroutine, *args, **kwargs):
        self.spawn(coroutine(*args, **kwargs))
        self.loop()

    def want_read(self, sock: socket.socket):
        """Handler for the 'want_read' event, performs the needed operations to read from the passed socket
        asynchronously"""

        self.selector.register(sock, EVENT_READ, self.running)

    def want_write(self, sock: socket.socket):
        """Handler for the 'want_write' event, performs the needed operations to write into the passed socket
        asynchronously"""

        self.selector.register(sock, EVENT_WRITE, self.running)

    def wrap_socket(self, sock):
        return AsyncSocket(sock, self)

    async def read_sock(self, sock: socket.socket, buffer: int):
        await want_read(sock)
        return sock.recv(buffer)

    async def accept_sock(self, sock: socket.socket):
        await want_read(sock)
        return sock.accept()

    async def sock_sendall(self, sock: socket.socket, data: bytes):
        while data:
            await want_write(sock)
            sent_no = sock.send(data)
            data = data[sent_no:]

    async def close_sock(self, sock: socket.socket):
        await want_write(sock)
        return sock.close()

    def want_join(self, coro: types.coroutine):
        if coro not in self.joined:
            self.joined[coro].append(self.running)
        else:
            raise AlreadyJoinedError("Joining the same task multiple times is not allowed!")

    def want_sleep(self, seconds):
        heappush(self.paused, (self.clock() + seconds, self.running))

    def want_cancel(self, task):
        task.coroutine.throw(CancelledError)

    async def connect_sock(self, sock: socket.socket, addr: tuple):
        await want_write(sock)
        return sock.connect(addr)


@types.coroutine
def sleep(seconds: int):
    """Pause the execution of a coroutine for the passed amount of seconds,
    without blocking the entire event loop, which keeps watching for other events"""

    yield "want_sleep", seconds


@types.coroutine
def want_read(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to read from the passed socket"""

    yield "want_read", sock


@types.coroutine
def want_write(sock: socket.socket):
    """'Tells' the event loop that there is some coroutine that wants to write into the passed socket"""

    yield "want_write", sock


@types.coroutine
def join(task: Task):
    """'Tells' the scheduler that the desired task MUST be awaited for completion"""

    task.joined = True
    yield "want_join", task
    if task.exception:
        print("Traceback (most recent call last):")
        traceback.print_tb(task.exception.__traceback__)
        exception_name = type(task.exception).__name__
        if str(task.exception):
            print(f"{exception_name}: {task.exception}")
        else:
            print(task.exception)
        raise task.exception
    return task.ret_val


@types.coroutine
def cancel(task: Task):
    yield "want_cancel", task
    assert task.cancelled

