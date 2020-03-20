import giambio


loop = giambio.EventLoop()

"""

What works and what does not

- Run tasks concurrently: V
- Join mechanism: V
- Sleep mechanism: V
- Cancellation mechanism: V
- Exception propagation: V
- Concurrent I/O: X   Note: I/O would work only when a task is joined (weird)
- Return values of coroutines: X     Note: Return values ARE actually stored in task objects properly, but are messed up later when joining tasks

"""

async def countdown(n):
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await giambio.sleep(1)
    return "Count DOWN over"


async def count(stop, step=1):
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += step
        await giambio.sleep(step)
    return "Count UP over"


async def main():
    task = loop.spawn(countdown(8))
    task1 = loop.spawn(count(8, 2))
    print(await giambio.join(task))
    print(await giambio.join(task1))

loop.start(main)
