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
A library like giambio comes into play when you need to perform lots of [blocking operations](https://en.wikipedia.org/wiki/Blocking_(computing)), 
and network servers happens to be heavily based on I/O: a blocking operation. 
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

__Side note__: If you have decent knowledge about asynchronous python, you might have noticed that we haven't mentioned coroutines
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
Yep, you read that right. 

To demonstrate this, have a look a this example


```python
import giambio

async def countdown(n: int):
    print(f"Counting down from {n}!")
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await giambio.sleep(1)
    print("Countdown over")
    return 0

async def countup(stop: int):
    print(f"Counting up to {stop}!")
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += 1
        await giambio.sleep(2)
    print("Countup over")
    return 1

async def main():
    start = giambio.clock()
    async with giambio.create_pool() as pool:
        pool.spawn(countdown, 10)
        pool.spawn(countup, 5)
        print("Children spawned, awaiting completion")
    print(f"Task execution complete in {giambio.clock() - start:2f} seconds")

if __name__ == "__main__":
    giambio.run(main)

```

There is a lot going on here, and we'll explain every bit of it step by step:

- First, we imported giambio and defined two async functions: `countup` and `countdown`
- These two functions do exactly what their name suggests, but for the purposes of
this tutorial, `countup` will be running twice as slow as `countdown` (see the call
to `await giambio.sleep(2)`?)
- Here comes the real fun: `async with`? What's going on there?
As it turns out, Python 3.5 didn't just add async functions, but also quite a bit
of related new syntax. One of the things that was added is asynchronous context managers.
You might have already encountered context managers in python, but in case you didn't,
a line such as `with foo as sth` tells the Python interpreter to call `foo.__enter__()`
at the beginning of the block, and `foo.__exit__()` at the end of the block. The `as`
keyword just assigns the return value of `foo.__enter__()` to the variable `sth`. So
context managers are a shorthand for calling functions, and since Python 3.5 added
async functions, we also needed async context managers. While `with foo as sth` calls
`foo.__enter__()`, `async with foo as sth` calls `await foo.__aenter__()`, easy huh?

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
calls the pool's `__aexit__()` method. What this does is pause the parent task (our `main`
async function in this case) until all children task have exited, and as it turns out, that
is a good thing.
The reason why pools always wait for all children to have finished executing is that it makes
easier propagating exceptions in the parent if something goes wrong: unlike many other frameworks,
exceptions in giambio always behave as expected


Ok, so, let's try running this snippet and see what we get:

```
Children spawned, awaiting completion
Counting down from 10!
Down 10
Counting up to 5!
Up 0
Down 9
Up 1
Down 8
Down 7
Up 2
Down 6
Down 5
Up 3
Down 4
Down 3
Up 4
Down 2
Down 1
Countup over
Countdown over
Task execution complete in 10.07 seconds
```

(Your output might have some lines swapped compared to this)

You see how `countup` and `countdown` both start and finish
together? Moreover, even though each function slept for about 10
seconds (therefore 20 seconds total), the program just took 10
seconds to complete, so our children are really running at the same time.

If you've ever done thread programming, this will feel like home, and that's good: 
that's exactly what we want. But beware! No threads are involved here, giambio is
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
to reason about, because you can immediately statically infer if function will ever switch, and where
will it do so, unlike threads which can (and will) switch whenever they feel like it.

Remember when we talked about checkpoints? That's what they are: async functions that allow giambio
to switch tasks. The problem with checkpoints is that if you don't have enough of them in your code,
then giambio will switch less frequently, hurting concurrency. It turns out that a quick and easy fix
for that is calling `await giambio.sleep(0)`; This will implicitly let giambio kick in and do its job,
and it will reschedule the caller almost immediately, because the sleep time is 0.

### Mix and match? No thanks

You may wonder whether you can mix async libraries: for instance, can we call `trio.sleep` in a 
giambio application? The answer is no, we can't, and there's a reason for that. Giambio wraps all
your asynchronous code in its event loop, which is what actually runs the tasks. When you call
`await giambio.something()`, what you're doing is sending "commands" to the event loop asking it
to perform a certain thing in a given task, and to communicate your intent to the loop, the
primitives (such as `giambio.sleep`) talk a language that only giambio's event loop can understand. 
Other libraries have other private "languages", so mixing them is not possible: doing so will cause 
giambio to get very confused and most likely just explode spectacularly badly


## Contributing

This is a relatively young project and it is looking for collaborators! It's not rocket science, 
but writing a proper framework like this implies some non-trivial issues that require proper and optimized solutions, 
so if you feel like you want to challenge yourself don't hesitate to contact me on [Telegram](https://telegram.me/nocturn9x)
or by [E-mail](mailto:hackhab@gmail.com)
