import giambio
from debugger import Debugger


async def child():
    print("[child] Child spawned!! Sleeping for 5 seconds")
    await giambio.sleep(5)
    print("[child] Had a nice nap!")


async def child1():
    print("[child 1] Child spawned!! Sleeping for 2 seconds")
    await giambio.sleep(2)
    print("[child 1] Had a nice nap, suiciding now!")
    raise TypeError("rip")  # Watch the exception magically propagate!


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
            # This pool will run until completion of its
            # tasks and then propagate the exception. This is
            # because exception in nested pools are propagated
            # all the way down first, then the pools above the
            # one that raised the error first wait for their
            # children to complete and only then re-raise the original exception
            await pool.spawn(child)
            await pool.spawn(child)
            print("[main] First 2 children spawned, awaiting completion")
            async with giambio.create_pool() as a_pool:
                await a_pool.spawn(child1)
                print("[main] Third children spawned, prepare for trouble in 2 seconds")
                async with giambio.create_pool() as new_pool:
                    # This pool will be cancelled by the exception
                    # in the outer pool
                    await new_pool.spawn(child2)
                    await new_pool.spawn(child3)
                    print("[main] Fourth and fifth children spawned")
    except Exception as error:
        # Because exceptions just *work*!
        print(f"[main] Exception from child caught! {repr(error)}")
    print(f"[main] Children execution complete in {giambio.clock() - start:.2f} seconds")


if __name__ == "__main__":
    giambio.run(main, debugger=())
