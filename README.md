# giambio
Giambio: Asynchronous Python made easy (and friendly)


# What's that?

giambio is a Python framework that implements the aysnchronous mechanism and allow to perform I/O multiplexing and basically do more than one thing at once.
This library implements what is known as a stackless mode of execution, or "green threads", though the latter term is misleading as **no multithreading is involved**.
        

## Disclaimer

Right now this is no more than a toy implementation to help me understand how Python and async work, but it will (hopefully) become a production ready library soon


## A small explanation

Libraries like giambio shine the most when it comes to performing asyncronous I/O (reading a socket, writing to a file, stuff like that).

The most common example of this is a network server, which just can't be handling one client at a time only.

One possible approach to achieve concurrency is to use threads, and despite their bad reputation in Python due to the GIL, they actually might be a good choice when it comes to I/O (it is performed out of control of the GIL so that isn't trotthled like CPU-intensive tasks). Problem is, if you have 10000 concurrent connections, you would need to set a limit to the number of threads that can be spawned (you definitely don't want to spawn 10 thousands threads do you?). On top of that, threads are known to be tricky when it comes to synchronization and coordination, so in general you'll hear anyone yelling at you "Don't use threads!". That's when libraries like giambio come in handy!

A library like giambio implements some low-level primitives and a main loop (known as an **Event Loop**) that acts like a kernel: If a function needs a "system" call (in this case it's I/O) it will trigger a trap and stop, waiting for the event loop to return execution control and proceed. In the meantime, the loop catches the trap and uses its associated metadata to perform the requested operation. But since I/O 99% of the times implies waiting for a resource to become available, the loop will also run other tasks while it's waiting for that I/O to happen.

And that's how it works!


## Let's code

Now you might think _"That's cool and neat and everything, but how do I use it?"_, and you're right. Let's write some code with giambio!


giambio has been designed with simplicity in mind and to expose a clean API to its users, so this README won't go deep in the explanation of what a coroutine is. For the sake of this tutorial all you need to know is that a coroutine is a function defined with `async def` instead of the regular `def`, that a coroutine can call other coroutines (while synchronous functions can't) and enables the Python 3.5 new feature, which is `await` (basically an abstraction layer for `yield`)

Just to clarify things, giambio does not avoid the Global Interpreter Lock nor it performs any sort of multithreading or multiprocessing (at least by default). Remember **concurrency is not parallelism**, concurrent tasks will switch back and forth and proceed with their calculations but won't be running independently like they would do if they were forked off to a process pool. That's why it is called concurrency, because multiple tasks **concur** for the same amount of resources. (Which is basically the same things that happens inside your CPU at a much lower level, because processors run many more tasks than their number of logical cores)

Enough talking though, this is how a giambio based application looks like

```python

import giambio
import socket


loop = giambio.EventLoop()
addrs = ["example.com", "some-domain.tld", "other-site.net"]

async def io_bound_task():
    res = []
    for addr in addrs:
        sock = loop.wrap_socket(socket.socket())  # This returns a new AsyncSocket object
        await sock.connect(addr)
        res.append(await sock.receive(1024))  # Get some data and append it to a list
        return res

async def main():
    task = await giambio.spawn(io_bound_task())
    task2 = await giambio.spawn(io_bound_task())  # Task object
    # These two will execute concurrently!

loop.start(main)  # Note the absence of parentheses
```
