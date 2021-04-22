import giambio
from debugger import Debugger


async def child(name: int):
    print(f"[child {name}] Child spawned!! Sleeping for {name} seconds")
    await giambio.sleep(name)
    print(f"[child {name}] Had a nice nap!")


async def main():
    start = giambio.clock()
    async with giambio.create_pool() as pool:
        pool.spawn(child, 1)
        pool.spawn(child, 2)
        async with giambio.create_pool() as a_pool:
            a_pool.spawn(child, 3)
            a_pool.spawn(child, 4)
            print("[main] Children spawned, awaiting completion")
    # This will *only* execute when everything inside the async with block
    # has ran, including any other pool
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())