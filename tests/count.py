from giambio import AsyncScheduler, sleep


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
    cup = scheduler.create_task(countdown(10))
    cdown = scheduler.create_task(countup(5, 2))
    print("Counters started, awaiting completion")
    await cup.join()
    await cdown.join()
    print("Task execution complete")

if __name__ == "__main__":
    scheduler = AsyncScheduler()
    try:
        scheduler.start(main())
    except Exception:
        print("main() errored!")

