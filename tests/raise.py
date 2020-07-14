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


async def countdown2(n: int):
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await giambio.sleep(1)
        raise Exception("bruh")
    print("Countdown over")
    return 0


async def main():
    try:
        async with giambio.TaskManager(scheduler) as manager:
            cup = manager.create_task(countup(5, 2))
            cdown = manager.create_task(countdown(10))
#            cdown2 = manager.create_task(countdown2(5))
            print("Counters started, awaiting completion")
    except Exception as err:
        print(f"An error occurred!\n{type(err).__name__}: {err}")
    print("Task execution complete")


if __name__ == "__main__":
    scheduler = giambio.AsyncScheduler()
    scheduler.start(main())
