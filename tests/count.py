import giambio


# A test for context managers


async def countdown(n: int):
    print(f"Counting down from {n}!")
    while n > 0:
        print(f"Down {n}")
        n -= 1
        await giambio.sleep(1)
#        raise Exception("oh no man")   # Uncomment to test propagation
    print("Countdown over")
    return 0


async def countup(stop: int, step: int = 1):
    print(f"Counting up to {stop}!")
    x = 0
    while x < stop:
        print(f"Up {x}")
        x += 1
        await giambio.sleep(step)
    print("Countup over")
    return 1


async def main():
    start = giambio.clock()
    try:
        async with giambio.create_pool() as pool:
            pool.spawn(countdown, 10)
            pool.spawn(countup, 5, 2)
            print("Children spawned, awaiting completion")
    except Exception as e:
        print(f"Got -> {type(e).__name__}: {e}")
    print(f"Task execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main)
