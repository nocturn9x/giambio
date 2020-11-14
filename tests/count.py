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
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += 1
        await giambio.sleep(step)
    print("Countup over")
    return 1


async def main():
    try:
        print("Creating an async pool")
        async with giambio.create_pool() as pool:
            print("Starting counters")
            pool.spawn(countdown, 10)
            count_up = pool.spawn(countup, 5, 2)
            # raise Exception
            # Raising an exception here has a weird
            # Behavior: The exception is propagated
            # *after* all the child tasks complete,
            # which is not what we want
            # print("Sleeping for 2 seconds before cancelling")
            # await giambio.sleep(2)
            # await count_up.cancel()      # TODO: Cancel _is_ broken, this does not re-schedule the parent!
            # print("Cancelled countup")
        print("Task execution complete")
    except Exception as e:
        print(f"Caught this bad boy in here, propagating it -> {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    print("Starting event loop")
    try:
        giambio.run(main)
    except BaseException as error:
        print(f"Exception caught from main event loop! -> {type(error).__name__}: {error}")
    print("Event loop done")
