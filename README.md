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

