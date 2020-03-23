import giambio
loop = giambio.EventLoop()

"""

What works and what does not (21st March 2020 11:22 AM)

- Run tasks concurrently: V
- Join mechanism: V
- Sleep mechanism: V
- Cancellation mechanism: V
- Exception propagation: V
- Concurrent I/O: X   Note: I/O would work only when a task is joined (weird)
- Return values of coroutines: V
- Scheduling tasks for future execution: X

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
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += step
        await giambio.sleep(step)
    print("Countup over")
    return "Count UP over"


async def main():
    print("Spawning countdown immediately, scheduling count for 2 secs from now")
    task = loop.spawn(countdown(8))
    task1 = loop.schedule(count(8, 2), 2)
    result = await task.join()
    result1 = await task1.join()   # Joining a scheduled task does not reschedule the parent task
    print(f"countdown returned: {result}\ncount returned: {result1}")
    print("All done")

loop.start(main)
