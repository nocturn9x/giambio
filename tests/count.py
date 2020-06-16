from giambio import AsyncScheduler, sleep, CancelledError
import time


async def countdown(n: int):
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await sleep(1)
    print("Countdown over")


async def countup(stop, step: int or float = 1):
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += 1
        await sleep(step)
    print("Countup over")


async def main():
    counter = scheduler.create_task(countup(5, 4))
    counter2 = scheduler.create_task(countdown(20))
    print("Counters started, awaiting completion")
    await sleep(4)
    print("4 seconds have passed, killing countup task")
    await counter.cancel()
    await counter.join()
    await counter2.join()
    print("Task execution complete")

if __name__ == "__main__":
    scheduler = AsyncScheduler()
    scheduler.start(main())

