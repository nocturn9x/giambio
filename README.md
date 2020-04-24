# giambio - Async Python made easy
Giambio: Asynchronous Python made easy (and friendly)


# What's that?

giambio is a Python framework that implements the aysnchronous mechanism and allow to perform I/O multiplexing and basically do more than one thing at once.
This library implements what is known as a stackless mode of execution, or "green threads", though the latter term is misleading as **no multithreading is involved**.
        

## Disclaimer

Right now this is no more than a toy implementation to help me understand how Python and async work, but it will (hopefully) become a production ready library soon

Also, this project was hugely inspired by the [curio project](https://github.com/dabeaz/curio) and the [trio project](https://github.com/python-trio/trio)

## A small explanation

Libraries like giambio shine the most when it comes to performing asyncronous I/O (reading a socket, writing to a file, stuff like that).

The most common example of this is a network server, which just can't be handling one client at a time only.

One possible approach to achieve concurrency is to use threads, and despite their bad reputation in Python due to the GIL, they actually might be a good choice when it comes to I/O because, like every system call, it is performed out of control of the GIL as it does not execute any Python code. Problem is, if you have 10000 concurrent connections, you would need to build a system that can scale without your users being randomly disconnected when the server is overloaded, and that also does not need to spawn 10 thousands threads on your machine. On top of that, to avoid messing things up, you would need what is known as _thread synchronization primitives_ and _thread pools_ to perform best. Such a big deal to run a web server, huh? That's when libraries like giambio come in handy!

A library like giambio implements some low-level primitives and an **Event Loop**, that acts like a kernel, running behind the scenes: If a function needs a "system" call (in this case it's I/O) it will trigger a trap and stop, waiting for the event loop to return execution control and proceed. In the meantime, the loop catches the trap and uses its associated metadata to perform the requested operation. But since I/O 99% of the times implies waiting for a resource to become available, the loop will also run other tasks while it's waiting for that I/O to happen.

And that's how it works!


## Some more context

giambio has been designed with simplicity in mind and to expose a clean API to its users, so this README won't go deep in the explanation of what a coroutine is. For the sake of this tutorial all you need to know is that a coroutine is a function defined with `async def` instead of the regular `def`, that a coroutine can call other coroutines (while synchronous functions can't) and enables the Python 3.5 new feature, which is `await` (basically an abstraction layer for `yield`)

Just to clarify things, giambio does not avoid the Global Interpreter Lock nor it performs any sort of multithreading or multiprocessing (at least by default). Remember that **concurrency is not parallelism**, concurrent tasks will switch back and forth and proceed with their calculations but won't be running independently like they would do if they were forked off to a process pool. That's why it is called concurrency, because multiple tasks **concur** for the same amount of resources. (Which is basically the same things that happens inside your CPU at a much lower level, because processors run many more tasks than their number of logical cores)

If you read carefully, you might now wonder: _"If a coroutine can call other coroutines, but synchronous functions cannot, how do I enter the async context in the first place?"_. This is done trough a special **synchronous function** (the `start()` method of an `EventLoop` object in our case) which can call asynchronous ones, that **must** be called from a synchronous context to avoid the library to explode spectacularly.

## Let's code

Enough talking though, this is how a giambio based application looks like

```python

import giambio
from giambio.socket import AsyncSocket
import socket
import logging

loop = giambio.EventLoop()

logging.basicConfig(level=20,
                    format="[%(levelname)s] %(asctime)s %(message)s",
                    datefmt='%d/%m/%Y %p')


async def make_srv(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(address)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.listen(5)
    asock = loop.wrap_socket(sock)    # This creates a socket that can be read asynchronously
    logging.info(f"Echo server serving asynchronously at {address}")
    async with giambio.TaskManager(loop) as manager:
        while True:
            conn, addr = await asock.accept()
            logging.info(f"{addr} connected")
            task = manager.spawn(echo_server(conn, addr))   # This spawns a new task


async def echo_server(sock: AsyncSocket, addr: tuple):
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


try:
    loop.start(make_srv, ('', 1501))
except KeyboardInterrupt:      # Because exceptions propagate
    print("Exiting...")
```

### Explanation

Ok, let's explain this code line by line:

- First, we imported the required libraries
- Then, we created our `EventLoop` object
- For the sake of this tutorial, we built the "Hello world" of network servers, an echo server. An echo server always replies to the client with the same data that it got from it
- Here comes the real fun: In our `make_srv` function, which is an `async` function, we used a Python 3 feature that might look weird and unfamiliar to newcomers (especially if you are used to asyncio or similar frameworks). Giambio takes advantage of the `async with` context manager to perform its magic: The `TaskManager` object is an ideal space where all tasks are spawned and run until they are done.

The usage of the context manager ensures lots of cool things: For example, the context manager won't exit unless ALL the tasks inside it completed their execution (either cancelled, errored, or returned), this also means that because tasks are always joined automatically you'll always get the return values of the coroutines and that exceptions will just **work as expected**.

You don't even need to be inside the with block to spawn tasks! All you need is a reference to the object, `manager` in this case, so you can even pass it as a parameter to a function and spawn tasks from another coroutine and still get all the guarantees that giambio ensures.

## Cancellation, exception propagation and other boring stuff

The only way to execute asynchronous code in giambio is trough a `TaskManager` (or one of its children classes) object used within an `async with` context manager. The `TaskManager` is an ideal "playground" where all asynchronous code runs and where the internal event loop of giambio can control its execution flow.

The key feature of this mechanism is that all tasks are always joined automatically: You'll never see a task running outside of the controlled context that giambio enforces.

Moreover, while most asynchronous frameworks out there would discard the return values from spawned tasks (in giambio "spawned" means that the coroutine was called using the `spawn()` or the `schedule()` method), here you'll never lose a single bit of information about your functions.
    

There are a few concepts to explain here, though:

 - The term "task" refers to a coroutine executed trough the `TaskManager`'s methods `spawn()` and `schedule()`, as well as one executed with ``await coro()``
 
 - Because of how the framework was designed, an exception in any of the task(s) inside the ``TaskManager`` will trigger the internal cancellation mechanism of giambio. All other running tasks are cancelled, read more below, and the exception(s) that caused the cancellation will be propagated inside the parent task as if you were running synchronous code
 
 - The concept of cancellation is a bit tricky, because there is no real way to stop a coroutine from executing without actually raising an exception inside it. So when giambio needs to cancel a task, it just throws `giambio.exceptions.CancelledError` inside it and hopes for the best.
 This exception inherits from `BaseException`, which by convention means that it should not be catched. Doing so in giambio will likely break your code and make it explode spectacularly; If you **really** want to catch it to perform some sort of cleanup, be sure to re-raise it when done.
 In general, when writing an asynchronous function in giambio, you should always bear in mind that it
 might be cancelled at any time and handle that case accordingly.
