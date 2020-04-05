import giambio

loop = giambio.EventLoop()

"""

What works and what does not (5 Apr 2020 12:06 AM):

- Run tasks concurrently: V
- Join mechanism: V
- Sleep mechanism: V
- Cancellation mechanism: V
- Exception propagation: X   Note: Almost ready
- Concurrent I/O: V
- Return values of coroutines: V
- Scheduling tasks for future execution: V
- Task Spawner (context manager): V


What's left to implement:

- An event system to wake up tasks programmatically
- Lower-level primitives such as locks, queues, semaphores
- File I/O (Also, consider that Windows won't allow select to work on non-socket fds)
- Complete the AsyncSocket implementation (happy eyeballs, other methods)
- Debugging tools
"""

async def countdown(n):
    try:
        while n > 0:
            print(f"Down {n}")
            n -= 1
            if n <= 2:          # Test an exception that triggers only sometimes
                raise ValueError
            await giambio.sleep(1)
        print("Countdown over")
        return "Count DOWN over"
    except giambio.CancelledError:
        print("countdown cancelled!")
        raise Exception("Oh no!")   # TODO Propagate this

async def count(stop, step=1):
    try:
        x = 0
        while x < stop:
            print(f"Up {x}")
            x += step
            await giambio.sleep(step)
        print("Countup over")
        return "Count UP over"
    except giambio.CancelledError:
        print("count cancelled!")
#        raise BaseException      # This will propagate

async def main():
    try:
        print("Spawning countdown immediately, scheduling count for 4 secs from now")
        async with giambio.TaskManager(loop) as manager:
            task = manager.spawn(countdown(8))
            task2 = manager.schedule(count(8, 2), 4)
            await task.cancel()   # This works, but other tasks continue running
        for task, ret in manager.values.items():
            print(f"Function '{task.coroutine.__name__}' at {hex(id(task.coroutine))} returned an object of type '{type(ret).__name__}': {repr(ret)}")
    except Exception as e:
        print(f"Actually I prefer to catch it here: {e}")  # Everything works just as expected, the try/except block below won't trigger


try:
    loop.start(main)
except Exception:      # Exceptions climb the whole stack
    print("Exceptions propagate!")
