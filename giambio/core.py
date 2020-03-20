import types
import datetime
from collections import deque, defaultdict
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from heapq import heappush, heappop
import socket
from .exceptions import GiambioError, AlreadyJoinedError, CancelledError
import traceback
from timeit import default_timer
from time import sleep as wait


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
        return f"<giambio.core.Task({self.coroutine}, {self.status}, {self.joined})"

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
            while self.selector.get_map():   # If there are sockets ready, schedule their associated task
                timeout = 0.0 if self.to_run else None
                tasks = deque(self.selector.select(timeout))
                for key, _ in tasks:
                    self.to_run.append(key.data)  # Socket ready? Schedule the task
                    self.selector.unregister(key.fileobj)  # Once scheduled, the task does not need to wait anymore
            while self.to_run or self.paused:
                if not self.to_run:
                    wait(max(0.0, self.paused[0][0] - self.clock()))  # If there are no tasks ready, just do nothing
                while self.paused and self.paused[0][0] < self.clock():  # Rechedules task when their timer has elapsed
                    _, coro = heappop(self.paused)
                    self.to_run.append(coro)
                self.running = self.to_run.popleft()  # Sets the currently running task
                try:
                    method, *args = self.running.run()  # Sneaky method call, thanks to David Beazley for this ;)
                    getattr(self, method)(*args)
                except StopIteration as e:
                    self.running.ret_value = e.args[0] if e.args else None  # Saves the return value
                    self.to_run.extend(self.joined.pop(self.running, ()))  # Reschedules the parent task
                except Exception as has_raised:
                    if self.running.joined:
                        self.running.exception = has_raised  # Errored? Save the exception
                    else:  # If the task is not joined, the exception would disappear, but not in giambio
                        raise
                    self.to_run.extend(self.joined.pop(self.running, ()))
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


class AsyncSocket(object):
    """Abstraction layer for asynchronous sockets"""

    def __init__(self, sock: socket.socket, loop: EventLoop):
        self.sock = sock
        self.sock.setblocking(False)
        self.loop = loop

    async def receive(self, max_size: int):
        """Receives up to max_size from a socket asynchronously"""

        return await self.loop.read_sock(self.sock, max_size)

    async def accept(self):
        """Accepts the socket, completing the 3-step TCP handshake asynchronously"""

        to_wrap = await self.loop.accept_sock(self.sock)
        return self.loop.wrap_socket(to_wrap[0]), to_wrap[1]

    async def send_all(self, data: bytes):
        """Sends all data inside the buffer asynchronously until it is empty"""

        return await self.loop.sock_sendall(self.sock, data)

    async def close(self):
        """Closes the socket asynchronously"""

        await self.loop.close_sock(self.sock)

    def __enter__(self):
        return self.sock.__enter__()

    def __exit__(self, *args):
        return self.sock.__exit__(*args)

    def __repr__(self):
        return f"AsyncSocket({self.sock}, {self.loop})"


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
        ename = type(task.exception).__name__
        if str(task.exception):
            print(f"{ename}: {task.exception}")
        else:
            print(task.exception)
        raise GiambioError from task.exception
    return task.ret_val


@types.coroutine
def cancel(task: Task):
    task.cancelled = True
    yield "want_cancel", task

