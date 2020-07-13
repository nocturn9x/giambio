import giambio


async def countdown(n: int):
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await giambio.sleep(1)
    print("Countdown over")
    return 0


async def countup(stop: int, step: int = 1):
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += 1
        await giambio.sleep(step)
    print("Countup over")
    return 1


async def main():
    cdown = scheduler.create_task(countdown(10))
    cup = scheduler.create_task(countup(5, 2))
    print("Counters started, awaiting completion")
    await giambio.sleep(2)
    print("Slept 2 seconds, killing countup")
    await cup.cancel()
    print("Countup cancelled")
    up = await cup.join()
    down = await cdown.join()
    print(f"Countup returned: {up}\nCountdown returned: {down}")
    print("Task execution complete")


if __name__ == "__main__":
    scheduler = giambio.AsyncScheduler()
    scheduler.start(main())
