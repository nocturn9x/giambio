# giambio - Asynchronous Python made easy (and friendly)

giambio is an event-driven concurrency library meant* to perform efficient and high-performant I/O multiplexing.
This library implements what is known as a _stackless mode of execution_, or
"green threads", though the latter term is misleading as **no multithreading is involved** (at least not by default).
        

_*_: The library *works* (sometimes), but its still in its very early stages and is nowhere close being
production ready, so be aware that it is likely that you'll find bugs and race conditions

## Disclaimer

Right now this is nothing more than a toy implementation to help me understand how this whole `async`/`await` thing works
and it is pretty much guaranteed to explode spectacularly badly while using it. If you find any bugs, please report them!
Oh and by the way, this project was hugely inspired by the [curio](https://github.com/dabeaz/curio) and the
[trio](https://github.com/python-trio/trio) projects, you might want to have a look at their amazing work if you need a
rock-solid and structured concurrency framework (I personally recommend trio and that's definitely not related to the fact
that most of the following text is ~~stolen~~ inspired from its documentation)


# What the hell is async anyway?

Libraries like giambio shine the most when it comes to performing asyncronous I/O (reading a socket, writing to a file, that sort of thing).
The most common example of this is a network server that needs to handle multiple connections at the same time.
One possible approach to achieve concurrency is to use threads, and despite their bad reputation in Python, they 
actually might be a good choice when it comes to I/O for reasons that span far beyond the scope of this tutorial.
If you choose to use threads, there are a couple things you can do, involving what is known as _thread synchronization 
primitives_ and _thread pools_, but once again that is beyond the purposes of this quickstart guide.
A library like giambio comes into play when you need to perform lots of [blocking operations](https://en.wikipedia.org/wiki/Blocking_(computing)
and network servers, among other things, happens to rely heavily on I/O which is a blocking operation. 
Starting to see where we're heading?


## A deeper dive

giambio has been designed with simplicity in mind, so this README won't explain all the gritty details about _how_ async is 
implemented in Python (you might want to check out [this article](https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/) if you want to learn more about all the implementation details).
For the sake of this tutorial, all you need to know is that functions defined giambio is all about a feature added in Python 3.5:
asynchronous functions, or 'async' for short.
Async functions are functions defined with `async def` instead of the regular `def`, like so:
```python

async def async_fun():   # An async function
    print("Hello, world!")

def sync_fun():     # A regular (sync) function
    print("Hello, world!")
```

First of all, async functions like to stick together: to call an async function you need to put `await` in front of it, like below:

```python
async def async_two():
    print("Hello from async_two!")
   
async def async_one():
    print("Hello from async_one!")
    await async_two()  # This is an async call
```

It has to be noted that using `await` outside of an async function is a `SyntaxError`, so basically async 
functions have a unique superpower: they can call other async functions. This already presents a chicken-and-egg 
problem, because when you fire up Python it is running plain ol' synchronous code, so how do we enter the async
context in the first place? That is done via a special _synchronous function_, `giambio.run` in our case, 
that has the ability to call asynchronous functions and can therefore initiate the async context. For this
reason, `giambio.run` **must** be called from a synchronous context, to avoid a horrible _deadlock_. Now
that you know all of this, you might be wondering why on earth would one use async functions instead of
regular functions: after all, their ability to call other async functions seems pretty pointless in itself, doesn't it?
Take a look at this example below: 

```python
import giambio

async def foo():
    print("Hello, world!")


giambio.run(foo)   # Prints 'Hello, world!'
```

This could as well be written the following way and would produce the same output:

```python
def foo():
    print("Hello, world!")

foo()   # Prints 'Hello, world!'
```

To answer this question, we have to dig a bit deeper about _what_ giambio gives you in exchange for all this `async`/`await` madness.
We already introduced `giambio.run`, a special runner function that can start the async context from a synchronous one, but giambio
provides also a set of tools, mainly for doing I/O. These functions, as you might have guessed, are async functions and they're useful!
So if you wanna take advantage of giambio, and hopefully you will after reading this guide, you need to write async code.
As an example, take this function using `giambio.sleep` (`giambio.sleep` is like `time.sleep`, but with an async flavor):

__Side note__: If you have decent knowledge about asynchronous python, you might have noticed that we haven't mentioned coroutines
so far. Don't worry, that is intentional: giambio never lets a user deal with coroutines on the surface because the whole async
model is much simpler if we take coroutines out of the game, and everything works just the same.

```python
import giambio


async def sleep_double(n):
    await giambio.sleep(2 * n)


giambio.run(sleep_double, 2)  # This hangs for 4 seconds and then returns
```

As it turns out, this function is one that's actually worth making async: because it calls another async function.
Not that there's nothing wrong with our `foo` from before, it surely works, but it doesn't really make sense to 
make it async in the first place.

### Don't forget the `await`!

As we already learned, async functions can only be called with the `await` keyword, so you would think that not
doing so would raise an error, but it's actually a little bit trickier than that. Take this example here

```python
import giambio


async def sleep_double_broken(n):
    print("Taking a nap!")
    start = giambio.clock()
    giambio.sleep(2 * n)    # We forgot the await!
    end = giambio.clock() - start
    print(f"Slept for {end:.2f} seconds!")


giambio.run(sleep_double_broken, 2)
```

Running this code, will produce an output that looks like this:

```
Taking a nap!
Slept 0.00 seconds!
__main__:7: RuntimeWarning: coroutine 'sleep' was never awaited
```

Wait, what happened here? From this output, it looks like the code worked, but something clearly went wrong:
the function didn't sleep. Python gives us a hint that we broke _something_ by raising a warning, complaining 
that `coroutine 'sleep' was never awaited` (you might not see this warning because it depends on whether a 
garbage collection cycle occurred or not). I know I said we weren't going to talk about coroutines, but you have
to blame Python, not me. Just know that if you see a warning like that, it means that somewhere in your code
you forgot an `await` when calling an async function, so try fixing that before trying to figure out what could
be the problem if you have a long traceback: most likely that's just collateral damage caused by the missing keyword.

If you're ok with just remembering to put `await` every time you call an async function you can safely skip to
the next section, but for the curios among y'all I might as well explain exactly what happened there.

When coroutines are called without the `await`, they don't exactly do nothing: they return this weird 'coroutine'
object

```python

>>> giambio.sleep(1)
<coroutine object sleep at 0x1069520d0>
```

The reason for this is that while giambio tries to separate the async and sync worlds, therefore considering
`await giambio.sleep(1)` as a single unit, when you `await` an async function Python does 2 things:
- It creates this weird coroutine object
- Passes that object to `await`, which runs the function

So basically that's why you always need to put `await` in front of an async function when calling it. 


## Something actually useful

Ok, so far you've learned that asynchronous functions can call other async functions, and that giambio has a special
runner function that can start the whole async context, but we didn't really do anything _useful_.
Our previous examples could be written using sync functions (like `time.sleep`) and they would work just fine, that isn't
quite useful is it?

But here comes the reason why you would want to use a library like giambio: it can run multiple async functions __at the same time__.
Yep, you read that right. To demnostrate this, have a look a this example


```python
import giambio


async def child(sleep: int, ident: int):
    start = giambio.clock()   # This returns the current time from giambio's perspective
    print(f"[child {ident}] Gonna sleep for {sleep} seconds!")
    await giambio.sleep(sleep)
    end = giambio.clock() - start
    print(f"[child {ident}] I woke up! Slept for {end} seconds")


async def main():
    print("[parent] Spawning children")
    task = giambio.spawn(child, 1, 1)   # We spawn a child task
    task2 = giambio.spawn(child, 2, 2)  # and why not? another one!
    start = giambio.clock()
    print("[parent] Children spawned, awaiting completion")
    await task.join()
    await task2.join()
    end = giambio.clock() - start
    print(f"[parent] Execution terminated in {end} seconds")


if __name__ == "__main__":
    giambio.run(main)    # Start the async context
```

If you run that code, your output should look something like this (the order of the lines might be swapped):

```
[parent] Spawning children
[parent] Children spawned, awaiting completion
[child 1] Gonna sleep for 1 seconds!
[child 2] Gonna sleep for 2 seconds!
[...1 second passes...]
[child 1] I woke up! Slept for 1.004422144 seconds
[...another second passes...]
[child 2] I woke up! Slept for 2.0039494860000002 seconds
[parent] Execution terminated in 2.004069701 seconds
```

There is a lot going on here, and we'll explain every bit of it step by step:

TODO 

## Doing I/O

TODO

```python
import giambio
from giambio.socket import AsyncSocket
import socket
import logging


logging.basicConfig(
    level=20,
    format="[%(levelname)s] %(asctime)s %(message)s",
    datefmt="%d/%m/%Y %p"
    )


async def server(address: tuple):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # Create the socket object
    sock.bind(address)     # We bind to the address
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.listen(5)   # We start listening for connections, this must be done *before* wrapping the socket
    asock = giambio.wrap_socket(sock)   # We make the socket an async socket
    logging.info(f"Echo server serving asynchronously at {address}")
    while True:
        conn, addr = await asock.accept()   # Here we use our wrapper
        logging.info(f"{addr} connected")
        giambio.spawn(echo_handler, conn, addr)    # We spawn a child task and keep listening for other clients


async def echo_handler(sock: AsyncSocket, addr: tuple):
    async with sock:   # Handy trick that will automagically close the socket for us when we're done
        await sock.send_all(b"Welcome to the server pal, feel free to send me something!\n")
        while True:
            await sock.send_all(b"-> ")
            data = await sock.receive(1024)    # We get some data from the client
            if not data:
                break
            # Below there's some decoding/encoding mess that you can safely not care about
            to_send_back = data
            data = data.decode("utf-8").encode("unicode_escape")
            logging.info(f"Got: '{data.decode('utf-8')}' from {addr}")
            # And now we send back our reply!
            await sock.send_all(b"Got: " + to_send_back)
            logging.info(f"Echoed back '{data.decode('utf-8')}' to {addr}")
    # When we exit the context manager, the client has disconnected
    logging.info(f"Connection from {addr} closed")


if __name__ == "__main__":
    try:
        giambio.run(server, ("", 1501))
    except BaseException as error:  # Exceptions propagate!
        print(f"Exiting due to a {type(error).__name__}: '{error}'")
```


## Contributing

This is a relatively young project and it is looking for collaborators! It's not rocket science, 
but writing a proper framework like this implies some non-trivial issues that require proper and optimized solutions, 
so if you feel like you want to challenge yourself don't hesitate to contact me on [Telegram](https://telegram.me/isgiambyy)
or by [E-mail](mailto:hackhab@gmail.com)