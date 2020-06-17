import types
from collections import deque
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from heapq import heappush, heappop
import socket
from .exceptions import AlreadyJoinedError, CancelledError, GiambioError
from timeit import default_timer
from time import sleep as wait
from .socket import AsyncSocket, WantRead, WantWrite
from ._layers import Task
from socket import SOL_SOCKET, SO_ERROR
from ._traps import join, sleep, want_read, want_write, cancel


class AsyncScheduler:

    """Implementation of an event loop, alternates between execution of coroutines (asynchronous functions)
    to allow a concurrency model or 'green threads'"""

    def __init__(self):
        """Object constructor"""

        self.to_run = deque()  # Scheduled tasks
        self.paused = []  # Sleeping tasks
        self.selector = DefaultSelector()  # Selector object to perform I/O multiplexing
        self.running = None  # This will always point to the currently running coroutine (Task object)
        self.joined = {}  # Tasks that want to join
        self.clock = default_timer  # Monotonic clock to keep track of elapsed time
        self.sequence = 0  # To avoid TypeError in the (unlikely) event of two task with the same deadline we use a unique and incremental integer pushed to the queue together with the deadline and the function itself

    def run(self):
        """Main event loop for giambio"""

        while True:
            if not self.selector.get_map() and not any(deque(self.paused) + self.to_run):
                break
            if not self.to_run and self.paused:  # If there are sockets ready, (re)schedule their associated task
                wait(max(0.0, self.paused[0][0] - self.clock()))  # If there are no tasks ready, just do nothing
                while self.paused[0][0] < self.clock():  # Reschedules task when their timer has elapsed
                   _, __, coro = heappop(self.paused)
                   self.to_run.append(coro)
                   if not self.paused:
                       break
            timeout = 0.0 if self.to_run else None
            tasks = self.selector.select(timeout)
            for key, _ in tasks:
                self.to_run.append(key.data)  # Socket ready? Schedule the task
                self.selector.unregister(key.fileobj)  # Once (re)scheduled, the task does not need to perform I/O multiplexing (for now)
            while self.to_run:
                self.running = self.to_run.popleft()  # Sets the currently running task
                try:
                    method, *args = self.running.run()
                    getattr(self, method)(*args)   # Sneaky method call, thanks to David Beazley for this ;)
                except StopIteration as e:
                    e = e.args[0] if e.args else None
                    self.running.result = e
                    self.running.finished = True
                    self.reschedule_parent()
                except CancelledError:
                    self.running.cancelled = True
                    self.reschedule_parent()
                except Exception as error:
                    self.running.exc = error
                    self.reschedule_parent()

    def start(self, coro: types.coroutine):
        """Starts the event loop using a coroutine as an entry point.
           Equivalent to self.create_task(coro) and self.run()
        """

        self.to_run.append(Task(coro))
        self.run()

    def reschedule_parent(self):
        """Reschedules the parent task"""

        popped = self.joined.pop(self.running, None)
        if popped:
            self.to_run.append(popped)

    def want_read(self, sock: socket.socket):
        """Handler for the 'want_read' event, registers the socket inside the selector to perform I/0 multiplexing"""

        self.selector.register(sock, EVENT_READ, self.running)

    def want_write(self, sock: socket.socket):
        """Handler for the 'want_write' event, registers the socket inside the selector to perform I/0 multiplexing"""

        self.selector.register(sock, EVENT_WRITE, self.running)

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

    def join(self, coro: types.coroutine):
        """Handler for the 'want_join' event, does some magic to tell the scheduler
        to wait until the passed coroutine ends. The result of this call equals whatever the
        coroutine returns or, if an exception gets raised, the exception will get propagated inside the
        parent task"""


        if coro not in self.joined:
            self.joined[coro] = self.running
        else:
            raise AlreadyJoinedError("Joining the same task multiple times is not allowed!")

    def sleep(self, seconds):
        """Puts a task to sleep"""

        self.sequence += 1   # Make this specific sleeping task unique to avoid error when comparing identical deadlines
        heappush(self.paused, (self.clock() + seconds, self.sequence, self.running))
        self.running = None

    def cancel(self, task):
        """Cancels a task"""

        task.coroutine.throw(CancelledError)

    async def connect_sock(self, sock: socket.socket, addr: tuple):
        """Connects a socket asynchronously"""

        try:			# "Borrowed" from curio
            return sock.connect(addr)
        except WantWrite:
            await want_write(sock)
        err = sock.getsockopt(SOL_SOCKET, SO_ERROR)
        if err != 0:
            raise OSError(err, f'Connect call failed: {addr}')

    def create_task(self, coro: types.coroutine):
        """Creates a task and appends it to call stack"""

        task = Task(coro)
        self.to_run.append(task)
        return task
