import giambio
from debugger import Debugger


async def child():
    print("[child] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child] Had a nice nap!")
    raise TypeError("rip")  # Watch the exception magically propagate!


async def child1():
    print("[child 1] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 1] Had a nice nap!")


async def child2():
    print("[child 2] Child spawned!! Sleeping for 4 seconds")
    await giambio.sleep(4)
    print("[child 2] Had a nice nap!")


async def child3():
    print("[child 3] Child spawned!! Sleeping for 6 seconds")
    await giambio.sleep(6)
    print("[child 3] Had a nice nap!")


async def main():
    start = giambio.clock()
    try:
        async with giambio.create_pool() as pool:
            pool.spawn(child)
            pool.spawn(child1)
            print("[main] Children spawned, awaiting completion")
            async with giambio.create_pool() as new_pool:
                # This pool won't be affected from exceptions
                # in outer pools. This is a guarantee that giambio
                # ensures: an exception will only be propagated
                # after all enclosed task pools have exited
                new_pool.spawn(child2)
                new_pool.spawn(child3)
                print("[main] 3rd child spawned")
    except Exception as error:
        # Because exceptions just *work*!
        print(f"[main] Exception from child caught! {repr(error)}")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())
