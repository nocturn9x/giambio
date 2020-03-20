import giambio


loop = giambio.EventLoop()


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
