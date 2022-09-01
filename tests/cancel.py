import giambio
from debugger import Debugger


async def child(name: int):
    print(f"[child {name}] Child spawned!! Sleeping for {name} seconds")
    try:
        await giambio.sleep(name)
    except giambio.exceptions.CancelledError:
        # Perform some cleanup
        print(f"[child {name}] I have been cancelled!")
        raise  # Important! Not re-raising the exception *will* break giambio
    print(f"[child {name}] Had a nice nap!")


async def main():
    start = giambio.clock()
    async with giambio.create_pool() as pool:
        await pool.spawn(child, 1)  # If you comment this line, the pool will exit immediately!
        task = await pool.spawn(child, 2)
        print("[main] Children spawned, awaiting completion")
        await task.cancel()
        print("[main] Second child cancelled")
    # This code always executes, no matter what happens inside the pool (unless an exception
    # is raised)
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())
