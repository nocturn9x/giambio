from debugger import Debugger
import giambio


# A test for events


async def child(ev: giambio.Event, pause: int):
    print("[child] Child is alive! Going to wait until notified")
    start_total = giambio.clock()
    data = await ev.wait()
    end_pause = giambio.clock() - start_total
    print(f"[child] Parent set the event with value {data}, exiting in {pause} seconds")
    start_sleep = giambio.clock()
    await giambio.sleep(pause)
    end_sleep = giambio.clock() - start_sleep
    end_total = giambio.clock() - start_total
    print(
        f"[child] Done! Slept for {end_total:.2f} seconds total ({end_pause:.2f} waiting, {end_sleep:.2f} sleeping), nice nap!"
    )


async def parent(pause: int = 1):
    async with giambio.skip_after(5) as pool:
        # The pool created by skip_after will
        # just silently keep going after 5
        # seconds and raise no error
        event = giambio.Event()
        print("[parent] Spawning child task")
        await pool.spawn(child, event, pause + 2)
        start = giambio.clock()
        print(f"[parent] Sleeping {pause} second(s) before setting the event")
        await giambio.sleep(pause)
        await event.trigger(True)
        print("[parent] Event set, awaiting child completion")
    end = giambio.clock() - start
    if pool.timed_out:
        print("[parent] Timeout has expired!")
    print(f"[parent] Child exited in {end:.2f} seconds")


if __name__ == "__main__":
    giambio.run(parent, 2, debugger=())
