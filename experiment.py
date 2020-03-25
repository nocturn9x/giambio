import giambio

loop = giambio.EventLoop()

"""

What works and what does not (23rd March 2020 23:24 PM)

- Run tasks concurrently: V
- Join mechanism: V
- Sleep mechanism: V
- Cancellation mechanism: X  Note: Figure out how to rescheule parent task
- Exception propagation: V
- Concurrent I/O: V
- Return values of coroutines: V
- Scheduling tasks for future execution: V
- Task Spawner (context manager): X  Note: Not Implemented

"""

async def countdown(n):
    try:
        while n > 0:
            print(f"Down {n}")
            n -= 1
            await giambio.sleep(1)
        print("Countdown over")
        return "Count DOWN over"
    except giambio.CancelledError:
        print("countdown cancelled!")


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
        task = await manager.spawn(countdown(4))
        await manager.schedule(count(8, 2), 4)
        await task.cancel()
    for task, ret in manager.values.items():
        print(f"Function '{task.coroutine.__name__}' at {hex(id(task.coroutine))} returned an object of type '{type(ret).__name__}': {repr(ret)}")


loop.start(main)
