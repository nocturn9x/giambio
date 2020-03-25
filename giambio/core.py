import types
from collections import deque, defaultdict
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from heapq import heappush, heappop
import socket
from .exceptions import AlreadyJoinedError, CancelledError
from timeit import default_timer
from time import sleep as wait
from .socket import AsyncSocket, WantRead, WantWrite
from .abstractions import Task, Result
from socket import SOL_SOCKET, SO_ERROR
from .traps import join, sleep, want_read, want_write, cancel

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
        self.sequence = 0  # To avoid TypeError in the (unlikely) event of two task with the same deadline we use a unique and incremental integer pushed to the queue together with the deadline and the function itself

    def loop(self):
        """Main event loop for giambio"""

        while True:
            if not self.selector.get_map() and not any((self.to_run + deque(self.paused))):
                break
            while not self.to_run:  # If there are sockets ready, (re)schedule their associated task
                timeout = 0.0 if self.to_run else None
                tasks = self.selector.select(timeout)
                for key, _ in tasks:
                    self.to_run.append(key.data)  # Socket ready? Schedule the task
                    self.selector.unregister(key.fileobj)  # Once (re)scheduled, the task does not need to perform I/O multiplexing (for now)
            while self.to_run or self.paused:
                if not self.to_run:
                    wait(max(0.0, self.paused[0][0] - self.clock()))  # If there are no tasks ready, just do nothing
                while self.paused and self.paused[0][0] < self.clock():  # Reschedules task when their timer has elapsed
                    _, __, coro = heappop(self.paused)
                    self.to_run.append(coro)
                self.running = self.to_run.popleft()  # Sets the currently running task
                try:
                    method, *args = self.running.run()
                    getattr(self, method)(*args)   # Sneaky method call, thanks to David Beazley for this ;)
                except StopIteration as e:
                    self.running.result = Result(e.args[0] if e.args else None, None)  # Saves the return value
                    self.to_run.extend(self.joined.pop(self.running, ()))  # Reschedules the parent task
                except RuntimeError:
                    self.to_run.extend(self.joined.pop(self.running, ()))   # Reschedules the parent task
                    self.to_run.append(self.running)
                except Exception as has_raised:
                    self.to_run.extend(self.joined.pop(self.running, ()))  # Reschedules the parent task
                    if self.running.joined:    # Let the join function handle the hassle of propagating the error
                        self.running.result = Result(None, has_raised)  # Save the exception
                    else:  # Let the exception propagate (I'm looking at you asyncIO ;))
                        raise
                except KeyboardInterrupt:
                    self.running.throw(KeyboardInterrupt)

    def spawn(self, coroutine: types.coroutine):
        """Schedules a task for execution, appending it to the call stack"""

        task = Task(coroutine, self)
        self.to_run.append(task)
        return task

    def schedule(self, coroutine: types.coroutine, when: int):
        """Schedules a task for execution after n seconds"""

        self.sequence += 1
        task = Task(coroutine, self)
        heappush(self.paused, (self.clock() + when, self.sequence, task))
        return task

    def start(self, coroutine: types.coroutine, *args, **kwargs):
        """Starts the event loop"""

        self.spawn(coroutine(*args, **kwargs))
        self.loop()

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

    def want_join(self, coro: types.coroutine):
        """Handler for the 'want_join' event, does some magic to tell the scheduler
        to wait until the passed coroutine ends. The result of this call equals whatever the
        coroutine returns or, if an exception gets raised, the exception will get propagated inside the
        parent task"""

        if coro not in self.joined:
            self.joined[coro].append(self.running)
        else:
            self.running.throw(AlreadyJoinedError("Joining the same task multiple times is not allowed!"))

    def want_sleep(self, seconds):
        if seconds > 0:    # If seconds <= 0 this function just acts as a checkpoint
            self.sequence += 1   # Make this specific sleeping task unique to avoid error when comparing identical deadlines
            heappush(self.paused, (self.clock() + seconds, self.sequence, self.running))
        else:
            self.to_run.append(self.running)    # Reschedule the task that called sleep

    def want_cancel(self, task):
        task.cancelled = True
        self.to_run.extend(self.joined.pop(self.running, ()))
        self.to_run.append(self.running)   # Reschedules the parent task
        task.throw(CancelledError())

    async def connect_sock(self, sock: socket.socket, addr: tuple):
        try:			# "Borrowed" from curio
            result = sock.connect(addr)
            return result
        except WantWrite:
            await want_write(sock)
        err = sock.getsockopt(SOL_SOCKET, SO_ERROR)
        if err != 0:
            raise OSError(err, f'Connect call failed {addr}')
