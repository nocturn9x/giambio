import giambio

loop = giambio.EventLoop()

"""

What works and what does not (25th March 2020 20:35)

- Run tasks concurrently: V
- Join mechanism: V
- Sleep mechanism: V
- Cancellation mechanism: V
- Exception propagation: X
- Concurrent I/O: V
- Return values of coroutines: V
- Scheduling tasks for future execution: V
- Task Spawner (context manager): V

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
        raise Exception("Oh no!")   #TODO Propagate this

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


async def main():
        print("Spawning countdown immediately, scheduling count for 4 secs from now")
        async with giambio.TaskManager(loop) as manager:
            task = manager.spawn(countdown(8))
            manager.schedule(count(8, 2), 4)
        for task, ret in manager.values.items():
            print(f"Function '{task.coroutine.__name__}' at {hex(id(task.coroutine))} returned an object of type '{type(ret).__name__}': {repr(ret)}")


loop.start(main)

