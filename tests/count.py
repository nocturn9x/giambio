from giambio import AsyncScheduler, sleep, TaskManager
import time


async def countdown(n: int):
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await sleep(1)
        if n == 5:
            raise ValueError('lul')
    print("Countdown over")


async def countup(stop, step: int or float = 1):
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += 1
        await sleep(step)
    print("Countup over")


async def main():
    async with TaskManager(scheduler) as manager:
        manager.spawn(countdown(10))
        manager.spawn(countup(5, 2))
        print("Counters started, awaiting completion")
    print("Task execution complete")

if __name__ == "__main__":
    scheduler = AsyncScheduler()
    scheduler.start(main())

