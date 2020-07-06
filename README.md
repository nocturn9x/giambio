# giambio - Asynchronous Python made easy (and friendly)

giambio is an event-driven concurrency library suitable to perform efficient and high-performant I/O multiplexing.
This library implements what is known as a stackless mode of execution, or "green threads", though the latter term is misleading as **no multithreading is involved** (at least not by default).
        

## Disclaimer

Right now this is no more than a toy implementation to help me understand how Python and async work, but it will (hopefully) become a production ready library soon

Also, this project was hugely inspired by the [curio project](https://github.com/dabeaz/curio) and the [trio project](https://github.com/python-trio/trio)

## Contributing

This is a relatively young project and it is looking for collaborators! It's not rocket science, but writing a proper framework like this implies some non-trivial issues that require proper and optimized solutions, so if you feel like you want to challenge yourself don't hesitate to contact me on [Telegram](https://telegram.me/isgiambyy) or by [E-mail](mailto:hackhab@gmail.com)

I'm no genius, I learned what I know from other people (reading articles, watching talks, failing to perform a certain task), so if you have enough experience with Python it's already enough!

## Welcome in the world of coroutines

Libraries like giambio shine the most when it comes to performing asyncronous I/O (reading a socket, writing to a file, stuff like that).

The most common example of this is a network server, which just can't be handling one client at a time only.

One possible approach to achieve concurrency is to use threads, and despite their bad reputation in Python due to the GIL, they actually might be a good choice when it comes to I/O because, like every system call, it is performed out of control of the GIL as it does not execute any Python code. Problem is, if you have 10000 concurrent connections, you would need to build a system that can scale without your users being randomly disconnected when the server is overloaded, and that also does not need to spawn 10 thousands threads on your machine. On top of that, to avoid messing things up, you would need what is known as _thread synchronization primitives_ and _thread pools_, to perform best. Such a big deal to run a web server, huh?

A library like giambio implements some low-level primitives (queues, semaphores, locks, events) and an **Event Loop**, that acts like a kernel, running behind the scenes: when a function needs to perform a [blocking operation](https://en.wikipedia.org/wiki/Blocking_(computing)), it will trigger a "trap" that notifies the event loop that a certain task wants to perform an operation on a certain resource. The loop catches the trap and uses its associated metadata to perform the requested operation as soon as possible (which means that the operation might be completed instantly, but it's not guaranteed). But since most of the times doing I/O implies waiting for a resource to become available, the loop will also run other tasks while it's waiting for that to happen.


### A deeper dive

giambio has been designed with simplicity in mind, so this README won't go deep in the explanation of what a coroutine is (you might want to check out [this article](https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/) if you want to learn more about all the implementation details and caveats about this). For the sake of this tutorial all you need to know is that a coroutine is a function defined with `async def` instead of the regular `def`, that a coroutine can call other coroutines, while _synchronous functions can't_, and that it enables the new Python 3.5 feature, which is the `await` keyword (basically an abstraction layer for `yield`).

Just to clarify things, giambio does not avoid the Global Interpreter Lock nor it performs any sort of multithreading or multiprocessing (at least by default). Remember that **concurrency is not parallelism**, concurrent tasks will switch back and forth and proceed with their calculations but won't be running independently like they would do if they were forked off to a process pool. That's why it is called concurrency, because multiple tasks **concur** for the same amount of resources. (Which is basically the same thing that happens inside your CPU at a much lower level, because processors run many more tasks than their actual number of cores)

If you read carefully, you might now wonder: _"If a coroutine can call other coroutines, but synchronous functions cannot, how do I enter the async context in the first place?"_. This is done trough a special **synchronous function** (the `start` method of an `AsyncScheduler` object in our case) which can call asynchronous ones, that **must** be called from a synchronous context to avoid a horrible *deadlock*.

## Let's code

Enough talking though, this is how a giambio based application looks like

```python
import giambio
import socket
import logging

sched = giambio.AsyncScheduler()

logging.basicConfig(level=20,
                    format="[%(levelname)s] %(asctime)s %(message)s",
                    datefmt='%d/%m/%Y %p')


async def server(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(address)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.listen(5)
    asock = sched.wrap_socket(sock)
    logging.info(f"Echo server serving asynchronously at {address}")
    while True:
        conn, addr = await asock.accept()
        logging.info(f"{addr} connected")
        sched.create_task(echo_handler(conn, addr))


async def echo_handler(sock: AsyncSocket, addr: tuple):
    with sock:
        await sock.send_all(b"Welcome to the server pal!\n")
        while True:
            data = await sock.receive(1000)
            if not data:
                break
            to_send_back = data
            data = data.decode("utf-8").encode('unicode_escape')
            logging.info(f"Got: '{data.decode('utf-8')}' from {addr}")
            await sock.send_all(b"Got: " + to_send_back)
            logging.info(f"Echoed back '{data.decode('utf-8')}' to {addr}")
    logging.info(f"Connection from {addr} closed")


if __name__ == "__main__":
    try:
        sched.start(server(('', 25000)))
    except KeyboardInterrupt:      # Exceptions propagate!
        print("Exiting...")
```

### Explanation

Ok, let's explain this code line by line:

- First, we imported the required libraries
- Then, we created an `AsyncScheduler` object
- For the sake of this tutorial, we built the "Hello world" of network servers, an echo server. An echo server always replies to the client with the same data that it got from it
- Here comes the real fun: In our `server` function, which is an `async` function, we used the `create_task` method of the scheduler object to spawn a new task. Pretty similar to the threaded model, but there are no threads involved!

Try using the `netcat` utility to connect to the server and instantiate multiple sessions to the server, you'll see that they are all connected simultaneously.

