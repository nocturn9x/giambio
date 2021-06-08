import giambio


async def child():
    print("[child] Child spawned!! Sleeping for 4 seconds")
    await giambio.sleep(4)
    print("[child] Had a nice nap!")


async def child1():
    print("[child 1] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 1] Had a nice nap!")


async def main():
    start = giambio.clock()
    async with giambio.create_pool() as pool:
        await pool.spawn(child)
        await pool.spawn(child1)
        print("[main] Children spawned, awaiting completion")
    print(
        f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds"
    )


if __name__ == "__main__":
    giambio.run(main)
