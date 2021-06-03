# Giambio - Asynchronous Python made easy (and friendly)

Giambio is an event-driven concurrency library meant* to perform efficient and high-performant I/O multiplexing.
This library implements what is known as a _stackless mode of execution_, or
"green threads", though the latter term is misleading as **no multithreading is involved** (at least not by default).


_*_: The library *works* (sometimes), but its still in its very early stages and is nowhere close being
production ready, so be aware that it is likely (if not guaranteed)  that you'll find bugs and race conditions

# Disclaimer

This project was hugely inspired by the [curio](https://github.com/dabeaz/curio) and the
[trio](https://github.com/python-trio/trio) projects, you might want to have a look at their amazing work if you need a
rock-solid and structured concurrency framework (I personally recommend trio and that's definitely not related to the fact
that most of the content of this document is ~~stolen~~ inspired from its documentation)


## Goals of this project

Making yet another async library might sound dumb in an already fragmented ecosystem like Python's.
In fact, giambio was initially born as a fun toy project to help me understand how this whole async/await magic actually worked, but while I researched this topic
further I found some issues with the current async ecosystem in Python.
As of the time of writing, the ecosystem for async libraries is divided as follows:
- Asyncio. Since it's in the stdlib, it sets a standard all of its own
- Tornado/Gevent/other old frameworks (based partly on asyncio or not)
- Modern, post PEP 492 frameworks like curio and trio

The main issue with asyncio is too complex to explain here in detail, but in short
it boils down to the fact that it is an old library which was not designed to take advantage
of the new async/await features natively and uses callbacks instead. There is a compatibility
layer to use async/await, but that only causes more problems because it still runs on top of the legacy
callback-based code (and it can't be used always, anyway). Asyncio has also a bunch
of problems with exception propagation and cancellation, which is an issue shared
by other old libraries like tornado and gevent.

To address this problem, a couple of very smart people came up with a new
paradigm called _Structured Concurrency_, which makes the async model much easier to use and
reason about. The two main players in this space are trio and curio.

Trio is an amazing library, probably the most advanced I've ever used, but for this exact
reason it has 2 main issues:
- The code is extremely intimidating to look at (without needing to be, read below)
- It has a lot, and I mean a LOT, of layers of indirections and fancy features that are useful, but also slow down execution


Curio has its own set of issues, namely:
- It allows orphaned tasks (i.e. tasks not spawned trough a `curio.TaskPool`), so it partially breaks structured concurrency
- It is not a community project, sadly
- Big chunks of code are completely undocumented: curio's loop is basically a black box to external code (and that's a design choice)

What I did love about curio though, is that its code is understandable once you go down the "writing an async scheduler" rabbithole, and it is in
fact my main source of ispiration for writing giambio as of now. Curio is also around 2 times faster than both trio and asyncio, according to benchmarks.

Giambio means to take the best of all of its predecessors, while being:
- Fully documented and type hinted for 100% editor coverage
- Small, but featureful 
- Fast, possibly as fast as curio, if not better
- Dependency-free: No fancy C modules, no external libraries, just pure idiomatic Python code
- Community-based: I frankly wouldn't have bothered making this if curio was open to community additions

## Current limitations

giambio is **highly** experimental and there's a lot to work to do before it's usable. Namely:
- Ensure cancellations work 100% of the time even when `await`ing functions and not spawning them
- Extend I/O functionality
- Add other task synchronization primitives such as locks and semaphores
- Documentation

# What the hell is async anyway?

Libraries like giambio shine the most when it comes to performing asynchronous I/O (reading from a socket, writing to a file, that sort of thing).
The most common example of this is a network server that needs to handle multiple connections at the same time.
One possible approach to achieve concurrency is to use threads, and despite their bad reputation in Python, they 
actually might be a good choice when it comes to I/O for reasons that span far beyond the scope of this document.
If you choose to use threads, there are a couple things you can do, involving what is known as _thread synchronization 
primitives_ and _thread pools_, but once again that is beyond the purposes of this quickstart guide.
A library like giambio comes into play when you need to perform lots of [blocking operations](https://en.wikipedia.org/wiki/Blocking_(computing)), 
and network servers happen to be heavily based on I/O: a blocking operation. 
Starting to see where we're heading?


## A deeper dive

Giambio has been designed with simplicity in mind, so this document won't explain all the gritty details about _how_ async is 
implemented in Python (you might want to check out [this article](https://snarky.ca/how-the-heck-does-async-await-work-in-python-3-5/) if you want to learn more about all the implementation details).
For the sake of this tutorial, all you need to know is that giambio is all about a feature added in Python 3.5:
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
functions have a unique superpower: they, and no-one else, can call other async functions.

This already presents a chicken-and-egg problem, because when you fire up Python, it is running plain ol'
synchronous code; So how do we enter the async context in the first place? 

That is done via a special _synchronous function_, `giambio.run` in our case, that has the ability to call 
asynchronous functions and can therefore initiate the async context. For this
reason, `giambio.run` **must** be called from a synchronous context, to avoid a horrible _deadlock_. 

Now that you know all of this, you might be wondering why on earth would one use async functions instead of
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

__Note__: If you have decent knowledge about asynchronous python, you might have noticed that we haven't mentioned coroutines
so far. Don't worry, that is intentional: giambio never lets a user deal with coroutines on the surface because the whole async
model is much simpler if we take coroutines out of the game, and everything works just the same.

```python
import giambio

async def sleep_double(n):
    await giambio.sleep(2 * n)

giambio.run(sleep_double, 2)  # This hangs for 4 seconds and returns
```

As it turns out, this function is one that's actually worth making async: because it calls another async function.
Not that there's nothing wrong with our `foo` from before, it surely works, but it doesn't really make sense to 
make it async in the first place.

### Don't forget the `await`!

As we already learned, async functions can only be called with the `await` keyword, and it would be logical to 
think that forgetting to do so would raise an error, but it's actually a little bit trickier than that. 

Take this example here:

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
garbage collection cycle occurred or not).
I know I said we weren't going to talk about coroutines, but you have to blame Python, not me. Just know that 
if you see a warning like that, it means that somewhere in your code you forgot an `await` when calling an async 
function, so try fixing that before trying to figure out what could be the problem if you have a long traceback: 
most likely that's just collateral damage caused by the missing keyword.

If you're ok with just remembering to put `await` every time you call an async function, you can safely skip to
the next section, but for the curios among y'all I might as well explain exactly what happened there.

When async functions are called without the `await`, they don't exactly do nothing: they return this weird 'coroutine'
object

```
>>> giambio.sleep(1)
<coroutine object sleep at 0x1069520d0>
```

The reason for this is that while giambio tries to separate the async and sync worlds, therefore considering
`await giambio.sleep(1)` as a single unit, when you `await` an async function Python does 2 things:
- It creates this weird coroutine object
- Passes that object to `await`, which runs the function

This is due to the fact that people started writing asynchronous Python code _before_ the `async`/`await` syntax was added, 
so many libraries (like asyncio) had to figure out some clever hacks to make it work without native support from the language
itself, taking advantage of generator functions (we'll talk about those later on), and coroutines are heavily based on generators.


## Something actually useful

Ok, so far you've learned that asynchronous functions can call other async functions, and that giambio has a special
runner function that can start the whole async context, but we didn't really do anything _useful_.
Our previous examples could be written using sync functions (like `time.sleep`) and they would work just fine, that isn't
quite useful is it?

But here's the plot twist: giambio can run multiple async functions __at the same time__.
Yep, you read that right. 

To demonstrate this, have a look a this example


```python
import giambio

async def child():
    print("[child] Child spawned! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child] Had a nice nap!")

async def child1():
    print("[child 1] Child spawned! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 1] Had a nice nap!")


async def main():
    start = giambio.clock()
    async with giambio.create_pool() as pool:
        pool.spawn(child)
        pool.spawn(child1)
        print("[main] Children spawned, awaiting completion")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main)
```

There is a lot going on here, and we'll explain every bit of it step by step:

- First, we imported giambio and defined two async functions: `child` and `child1`
- These two functions will just print something and then sleep for 2 seconds
- Here comes the real fun: `async with`? What's going on there?
As it turns out, Python 3.5 didn't just add async functions, but also quite a bit
of related new syntax. One of the things that was added is asynchronous context managers.
You might have already encountered context managers in python, but in case you didn't,
a line such as `with foo as sth` tells the Python interpreter to call `foo.__enter__()`
at the beginning of the block, and `foo.__exit__()` at the end of the block. The `as`
keyword just assigns the return value of `foo.__enter__()` to the variable `sth`. So
context managers are a shorthand for calling functions, and since Python 3.5 added
async functions, we also needed async context managers. While `with foo as sth` calls
`foo.__enter__()`, `async with foo as sth` calls `await foo.__aenter__()`: easy huh?

__Note__: On a related note, Python 3.5 also added asynchronous for loops! The logic is
the same though: while `for item in container` calls `container.__next__()` to fetch the
next item, `async for item in container` calls `await container.__anext__()` to do so.
It's _that_ simple, mostly just remember to stick `await` everywhere and you'll be good.

- Ok, so now we grasp `async with`, but what's with that `create_pool()`? In giambio,
there are actually 2 ways to call async functions: one we've already seen (`await fn()`),
while the other is trough an asynchronous pool. The cool part about `pool.spawn()` is 
that it will return immediately, without waiting for the async function to finish. So,
now our functions are running in the background.
After we spawn our tasks, we hit the call to `print` and the end of the block, so Python
`await`s the pool's `__aexit__()` method. What this does is pause the parent task (our `main`
async function in this case) until all children tasks have exited, and as it turns out, that
is a good thing.
The reason why pools always wait for all children to have finished executing is that it makes
easier propagating exceptions in the parent if something goes wrong: unlike many other frameworks,
exceptions in giambio always behave as expected


Ok, so, let's try running this snippet and see what we get:

```
[child] Child spawned!! Sleeping for 2 seconds
[child 1] Child spawned!! Sleeping for 2 seconds
[... 2 seconds pass ...]
[child] Had a nice nap!
[child 1] Had a nice nap!
[main] Children execution complete in 2.01 seconds
```

(Your output might have some lines swapped compared to this)

You see how `child` and `child1` both start and finish
together? Moreover, even though each function slept for about 2
seconds (therefore 4 seconds total), the program just took 2
seconds to complete, so our children are really running at the same time.

If you've ever done thread programming, this will feel like home, and that's good: 
it's exactly what we want. But beware! No threads are involved here, giambio is
running in a single thread. That's why we talked about _tasks_ rather than _threads_
so far. The difference between the two is that you can run a lot of tasks in a single
thread, and that with threads Python can switch which thread is running at any time.
Giambio, on the other hand, can switch tasks only at certain fixed points called 
_checkpoints_, more on that later.

### A sneak peak into the async world

The basic idea behind libraries like giambio is that they can run a lot of tasks
at the same time by switching back and forth between them at appropriate places.
An example for that could be a web server: while the server is waiting for a response
from a client, we can accept another connection. You don't necessarily need all these
pesky details to use giambio, but it's good to have at least an high-level understanding
of how this all works.

The peculiarity of asynchronous functions is that they can suspend their execution: that's
what `await` does, it yields back the execution control to giambio, which can then decide
what to do next.

To understand this better, take a look at this code:

```python
def countdown(n: int) -> int:
    while n:
        yield n
        n -= 1

for x in countdown(5):
    print(x)
```

In the above snippet, `countdown` is a generator function. Generators are really useful because
they allow to customize iteration. Running that code produces the following output:

```
5
4
3
2
1
```

The trick for this to work is `yield`.
What `yield` does is return back to the caller and suspend itself: In our case, `yield` 
returns to the for loop, which calls `countdown` again. So, the generator resumes right 
after the `yield`, decrements n, and loops right back to the top for the while loop to 
execute again. It's that suspension part that allows the async magic to happen: the whole 
`async`/`await` logic overlaps a lot with generator functions.

Some libraries, like `asyncio`, take advantage of this yielding mechanism, because they were made
way before Python 3.5 added that nice new syntax.

So, since only async functions can suspend themselves, the only places where giambio will switch
tasks is where there is a call to `await something()`. If there is no `await`, then you can be sure
that giambio will not switch tasks (because it can't): this makes the asynchronous model much easier
to reason about, because you can know if a function will ever switch, and where will it do so, just 
by looking at its source code. That is very different from what threads do: they can (and will) switch 
whenever they feel like it.

Remember when we talked about checkpoints? That's what they are: calls to async functions that allow 
giambio to switch tasks. The problem with checkpoints is that if you don't have enough of them in your code,
then giambio will switch less frequently, hurting concurrency. It turns out that a quick and easy fix
for that is calling `await giambio.sleep(0)`; This will implicitly let giambio kick in and do its job,
and it will reschedule the caller almost immediately, because the sleep time is 0.


### A closer look

In the above section we explained the theory behind async functions, but now we'll inspect the magic behind
`giambio.run()` and its event loop to demistify _how_ giambio makes this whole async thing happen. Luckily for us,
giambio has some useful tooling that lets us sneak peak inside the machinery of the library to better help us
understand what's going on, located at `giambio.debug.BaseDebugger`. That's an abstract class that we can customize
for our purposes and that communicates with the event loop about everything it's doing, so let's code it:

```python
class Debugger(giambio.debug.BaseDebugger):
    """
    A simple debugger for this test
    """

    def on_start(self):
        print("## Started running")

    def on_exit(self):
        print("## Finished running")

    def on_task_schedule(self, task, delay: int):
        print(f">> A task named '{task.name}' was scheduled to run in {delay:.2f} seconds")

    def on_task_spawn(self, task):
        print(f">> A task named '{task.name}' was spawned")
   
    def on_task_exit(self, task):
        print(f"<< Task '{task.name}' exited")
   
    def before_task_step(self, task):
        print(f"-> About to run a step for '{task.name}'")

    def after_task_step(self, task):
        print(f"<- Ran a step for '{task.name}'")

    def before_sleep(self, task, seconds):
        print(f"# About to put '{task.name}' to sleep for {seconds:.2f} seconds")
   
    def after_sleep(self, task, seconds):
        print(f"# Task '{task.name}' slept for {seconds:.2f} seconds")

    def before_io(self, timeout):
        print(f"!! About to check for I/O for up to {timeout:.2f} seconds")

    def after_io(self, timeout):
        print(f"!! Done I/O check (timeout {timeout:.2f} seconds)")

    def before_cancel(self, task):
        print(f"// About to cancel '{task.name}'")

    def after_cancel(self, task):
        print(f"// Cancelled '{task.name}'")
```

To use our debugger class, we need to pass it to `giambio.run()` using
the `debugger` keyword argument, like so:

```python
...
if __name__ == "__main__":
    giambio.run(main, debugger=Debugger())
```

__Note__: We passed an _instance_ (see the parentheses?) **not** a class

Running that modified code will produce a lot of output, and it should look something like this:

```
## Started running
-> About to run a step for 'main'
>> A task named 'child' was spawned
>> A task named 'child1' was spawned
[main] Children spawned, awaiting completion
<- Ran a step for 'main'
-> About to run a step for 'child'
[child] Child spawned!! Sleeping for 2 seconds
<- Ran a step for 'child'
# About to put 'child' to sleep for 2.00 seconds
-> About to run a step for 'child1'
[child 1] Child spawned!! Sleeping for 2 seconds
<- Ran a step for 'child1'
# About to put 'child1' to sleep for 2.00 seconds
[... 2 seconds pass ...]
# Task 'child' slept for 2.01 seconds
# Task 'child1' slept for 2.01 seconds
!! About to check for I/O for up to 0.00 seconds
!! Done I/O check (timeout 0.00 seconds)
-> About to run a step for 'child'
[child] Had a nice nap!
<< Task 'child' exited
-> About to run a step for 'child1'
[child 1] Had a nice nap!
<< Task 'child1' exited
-> About to run a step for 'main'
<- Ran a step for 'main'
-> About to run a step for 'main'
[main] Children execution complete in 2.01 seconds
<< Task 'main' exited
## Finished running
```

As expected, this prints _a lot_ of stuff, but let's start going trough it:
- First, we start the event loop: That's the call to `giambio.run()`
   ```
   ## Started running
   ```
- After that, we start running the `main` function
  ```
  -> About to run a step for 'main'
  ```
- When we run `main`, that enters the `async with` block and spawns our children,
  as well as execute our call to `print`
   ```
   >> A task named 'child' was spawned
   >> A task named 'child1' was spawned
   [main] Children spawned, awaiting completion
   ```
- After that, we hit the end of the block, so we pause and wait for our children
  to complete: That's when we start switching, and `child` can now run
  ```
  <- Ran a step for 'main'
  -> About to run a step for 'child'
  [child] Child spawned!! Sleeping for 2 seconds
  ```
- We're now at `await giambio.sleep(2)` inside `child`, and that puts it to sleep
  ```
  <- Ran a step for 'child'
  # About to put 'child' to sleep for 2.00 seconds
  ```
- Ok, so now `child` is asleep while `main` is waiting on its children, and `child1` can now execute,
  so giambio switches again and runs that
  ```
  -> About to run a step for 'child1'
  [child 1] Child spawned!! Sleeping for 2 seconds
  ```
- Now we hit the call to `await giambio.sleep(2)` inside `child1`, so that also goes to sleep
   ```
   <- Ran a step for 'child1'
   # About to put 'child1' to sleep for 2.00 seconds
   ```
- Since there is no other work to do, giambio just waits until it wakes up the two children,
  2 seconds later
  ```
  # Task 'child' slept for 2.01 seconds
  # Task 'child1' slept for 2.01 seconds
  ```
- Even though we're not doing any I/O here, giambio doesn't know that, so it
  does some checks (and finds out there is no I/O to do)
  ```
  !! About to check for I/O for up to 0.00 seconds
  !! Done I/O check (timeout 0.00 seconds)
  ```
- After 2 seconds have passed giambio wakes up our children and runs them until completion
  ```
  -> About to run a step for 'child'
  [child] Had a nice nap!
  << Task 'child' exited
  -> About to run a step for 'child1'
  [child 1] Had a nice nap!
  << Task 'child1' exited
  ```
- As promised, once all children exit, the parent task resumes and runs until it exits. This also
  causes the entire event loop to exit because there is nothing else to do
  ```
  -> About to run a step for 'main'
  <- Ran a step for 'main'
  -> About to run a step for 'main'
  [main] Children execution complete in 2.01 seconds
  << Task 'main' exited
  ## Finished running
  ```

So, in our example, our children run until they hit a call to `await giambio.sleep`, then execution control
goes back to `giambio.run`, which drives the execution for another step. This works because `giambio.sleep` and
`giambio.run` (as well as many others) work together to make this happen: `giambio.sleep` can pause the execution
of its children task and ask `giambio.run` to wake him up after a given amount of time.

__Note__: You may wonder whether you can mix async libraries: for instance, can we call `trio.sleep` in a 
giambio application? The answer is no, we can't, and this section explains why. When you call
`await giambio.sleep`, it asks `giambio.run` to pause the current task, and to do so it talks a language
that only `giambio.run` can understand. Other libraries have other private "languages", so mixing them is
not possible: doing so will cause giambio to get very confused and most likely just explode spectacularly badly.


## Doing I/O

I don't know about you, but to me all of the code we wrote so far was pretty boring. But here comes the fun part: now
I'll show you how to do actual work with giambio using its I/O primitives.

__Note__: As with everything in giambio, I/O support is limited and experimental. Any socket kind from python's builtin
socket module can be used with giambio, but other advanced features such as file I/O or memory channels simply don't
exist yet


### An echo server

For the purposes of this document, it's best to keep things simple, so we'll be writing the "Hello, world!" of
network servers: an echo server. An echo server simply replies to the client with the same data that it got from it

As always, I'll first throw the entire snippet at you and then disassemble it step by step, but since this code is
a little longer than usual we'll be dealing with one function at a time: first, let's write a function that can accept
clients and dispatch them to some other handler.

```python
import giambio
import logging


async def serve(bind_address: tuple):
    sock = giambio.socket.socket()
    await sock.bind(bind_address)
    await sock.listen(5)
    logging.info(f"Serving asynchronously at {bind_address[0]}:{bind_address[1]}")
    async with giambio.create_pool() as pool:
        while True:
            conn, address_tuple = await sock.accept()
            logging.info(f"{address_tuple[0]}:{address_tuple[1]} connected")
            pool.spawn(handler, conn, address_tuple)

```

So, our `serve` function does a few things:
- Sets up our server socket, just like in a synchronous server
- Opens a task pool and starts listening for clients in loop by using our new `giambio.socket.AsyncSocket` object
    - Notice how we use `await sock.accept()` and not `sock.accept()`, because that is an asynchronous socket!
- Once a client connects, we log some information, spawn a new task and pass it the client socket: that is our client handler

So, let's go over the declaration of `handler` then:

```python
async def handler(sock, client_address):
    address = f"{client_address[0]}:{client_address[1]}"
    async with sock:   # Closes the socket automatically
        await sock.send_all(b"Welcome to the server pal, feel free to send me something!\n")
        while True:
            await sock.send_all(b"-> ")
            data = await sock.receive(1024)
            if not data:
                break
            elif data == b"exit\n":
                await sock.send_all(b"Shutting down the server\n")
                raise Exception  # This kills the entire application!
            logging.info(f"Got: {data!r} from {address}")
            await sock.send_all(b"Got: " + data)
            logging.info(f"Echoed back {data!r} to {address}")
    logging.info(f"Connection from {address} closed")
```

This is where clients will be dispatched once they connect:
- First, we use the tuple that `serve` gave us to build a nice human-readable IP address
- giambio sockets support the context manager interface, just like regular sockets, so we use `async with sock` which
    will automatically close the socket for us when we're done using it
- Since we're nice people, we greet our users once they connect with a welcome message (notice: we sent **bytes**!)
    - As a side note, regular python sockets differentiate `sock.send` from `sock.sendall`: The difference is that `send` might
    not send the whole payload immediately, while `sendall` is just a wrapper around `send` in a loop which makes sure
    that all data is sent before returning. Since this difference is completely unnecessary and can lead to errors,
    giambio sockets only have a `send_all` method which **always** sends all the passed data before returning, but the
    naming was kept explicit because of the ambiguity caused by the builtin socket library.
- With the greetings out of the way, we enter a loop where we ask our client for data by using the `receive` method. Note that, just
    like regular python sockets' `recv` method, `receive` is guaranteed to return **at most** 1024 bytes, but **at least** 1 byte 
    (or any size in that range) depending on your OS buffers and network congestion
- We do a little check here: if what we receive is an empty message, then our client is gone and we can exit the loop
- Since I want to show off giambio's exception handling, I added a little if condition that will raise an exception if a client
    sends us a message with "exit" as content: this will propagate the exception in our `serve` function and kill all children tasks
- Here comes the "echo" part of "echo server": We log the message to the screen and then send the same data back to our client

Finally, some startup code:

```python

if __name__ == "__main__":
    logging.basicConfig(level=20, format="[%(levelname)s] %(asctime)s %(message)s", datefmt="%d/%m/%Y %p")
    try:
        giambio.run(serve, ("localhost", 1500))
    except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        if isinstance(error, KeyboardInterrupt):
            logging.info("Ctrl+C detected, exiting")
        else:
            logging.error(f"Exiting due to a {type(error).__name__}: {error}")
```

This looks fancy, but all it does is just run our server and catch any exception that might happen (because, again, exceptions are never discarded
in giambio): We differentiate KeyboardInterrupt from anything else because that is most likely us shutting down the server from the console.

So, putting everything together:

```python

import giambio
import socket
import logging


async def handler(sock, client_address):
    address = f"{client_address[0]}:{client_address[1]}"
    async with sock:   # Closes the socket automatically
        await sock.send_all(b"Welcome to the server pal, feel free to send me something!\n")
        while True:
            await sock.send_all(b"-> ")
            data = await sock.receive(1024)
            if not data:
                break
            elif data == b"exit\n":
                await sock.send_all(b"Shutting down the server\n")
                raise Exception  # This kills the entire application!
            logging.info(f"Got: {data!r} from {address}")
            await sock.send_all(b"Got: " + data)
            logging.info(f"Echoed back {data!r} to {address}")
    logging.info(f"Connection from {address} closed")


async def serve(bind_address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(bind_address)
    sock.listen(5)
    async_sock = giambio.wrap_socket(sock)   # We make the socket an async socket
    logging.info(f"Serving asynchronously at {bind_address[0]}:{bind_address[1]}")
    async with giambio.create_pool() as pool:
        while True:
            conn, address_tuple = await async_sock.accept()
            logging.info(f"{address_tuple[0]}:{address_tuple[1]} connected")
            pool.spawn(handler, conn, address_tuple)


if __name__ == "__main__":
    logging.basicConfig(level=20, format="[%(levelname)s] %(asctime)s %(message)s", datefmt="%d/%m/%Y %p")
    try:
        giambio.run(serve, ("localhost", 1500))
    except (Exception, KeyboardInterrupt) as error:  # Exceptions propagate!
        if isinstance(error, KeyboardInterrupt):
            logging.info("Ctrl+C detected, exiting")
        else:
            logging.error(f"Exiting due to a {type(error).__name__}: {error}")
```

Save this into a file and try running it, you should see something along the lines of:
```
[INFO] 22/04/2021 PM Serving asynchronously at localhost:1500

```
Yay! Our echo server is running, let's test it out by using the netcat terminal utility:
```
user@hostname:~ # nc localhost 1500
Welcome to the server pal, feel free to send me something!
-> async server test
Got: async server test
-> yay!
Got: yay!
```

And, on the server side...
```
[INFO] 22/04/2021 PM 127.0.0.1:52239 connected
[INFO] 22/04/2021 PM Got: b'async server test\n' from 127.0.0.1:52239
[INFO] 22/04/2021 PM Echoed back b'async server test\n' to 127.0.0.1:52239
[INFO] 22/04/2021 PM Got: b'yay!\n' from 127.0.0.1:52239
[INFO] 22/04/2021 PM Echoed back b'yay!\n' to 127.0.0.1:52239
```

Try opening more terminal windows concurrently and sending messages all at once, you'll see that they all
get replied to at the same time! That's the power of async.

Just to wrap up, try sending "exit" as a message:
```
-> exit
Shutting down the server
```

And on our server, as expected:
```
[ERROR] 22/04/2021 PM Exiting due to a Exception:
```

If you want to play around with this code you can also try pressing Ctrl+D/Ctrl+C on netcat to close your connection,
or Ctrl+C on the server's console to shut it down completely.

# Contributing

This is a relatively young project and it is looking for collaborators! It's not rocket science, 
but writing a proper framework like this implies some non-trivial issues that require proper and optimized solutions, 
so if you feel like you want to challenge yourself don't hesitate to contact me on [Telegram](https://telegram.me/nocturn9x)
or by [E-mail](mailto:hackhab@gmail.com)
