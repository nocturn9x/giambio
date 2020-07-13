import giambio


async def countdown(n: int):
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await giambio.sleep(1)
        raise TypeError(1)
    print("Countdown over")
    return 0


async def countup(stop: int, step: int = 1):
    try:
        x = 0
        while x < stop:
            print(f"Up {x}")
            x += 1
            await giambio.sleep(step)
        print("Countup over")
        return 1
    except giambio.exceptions.CancelledError:
        raise ValueError("Ciao")


async def main():
    try:
        async with giambio.TaskManager(scheduler) as manager:
            cdown = manager.create_task(countdown(10))
            cup = manager.create_task(countup(5, 2))
            print("Counters started, awaiting completion")
    except Exception:
        print("Exceptions propagate!")
    print("Task execution complete")


if __name__ == "__main__":
    scheduler = giambio.AsyncScheduler()
    scheduler.start(main())
