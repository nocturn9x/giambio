import giambio


# A test for context managers


async def countdown(n: int):
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await giambio.sleep(1)
        # raise Exception("oh no man")   # Uncomment to test propagation
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
        print("I'm not gonna die!!")
        raise BaseException(2)

async def main():
    try:
        print("Creating an async pool")
        async with giambio.create_pool() as pool:
            print("Starting counters")
            pool.spawn(countdown, 10)
            t = pool.spawn(countup, 5, 2)
            await giambio.sleep(2)
            await t.cancel()
        print("Task execution complete")
    except Exception as e:
        print(f"Caught this bad boy in here, propagating it -> {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    print("Starting event loop")
    try:
        giambio.run(main)
    except BaseException as e:
        print(f"Exception caught from main event loop!! -> {type(e).__name__}: {e}")
    print("Event loop done")
