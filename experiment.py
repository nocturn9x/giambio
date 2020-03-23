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
    except giambio.exceptions.CancelledError:
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
    except giambio.exceptions.CancelledError:
        print("count cancelled!")

async def main():
    print("Spawning countdown immediately, scheduling count for 4 secs from now")
    task = loop.spawn(countdown(8))
    task1 = loop.schedule(count(8, 2), 4)
    await giambio.sleep(0)  # Beware! Cancelling a task straight away will propagate the error in the parent
#    await task.cancel()    # TODO: Fix this to reschedule the parent task properly
    result = await task.join()
    result1 = await task1.join()
    print(f"countdown returned: {result}\ncount returned: {result1}")
    print("All done")

loop.start(main)
