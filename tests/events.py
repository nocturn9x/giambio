import giambio


async def child(notifier: giambio.Event, timeout: int):
    print("[child] Child is alive!")
    if timeout:
        print(f"[child] Waiting for events for up to {timeout} seconds")
    else:
        print("[child] Waiting for events")
    notification = await notifier.pause(timeout=timeout)
    if not notifier.event_caught:
        print("[child] Parent was too slow!")
    else:
        print(f"[child] Parent said: {notification}")

async def parent(pause: int = 1, child_timeout: int = 0):
    event = giambio.Event(scheduler)
    print("[parent] Spawning child task")
    task = scheduler.create_task(child(event, child_timeout))
    print(f"[parent] Sleeping {pause} second(s) before setting the event")
    await giambio.sleep(pause)
    print("[parent] Event set")
    await event.set("Hi, my child")
    if not event.event_caught:
        print("[parent] Event not delivered, the timeout has expired")
    else:
        print("[parent] Event delivered")
    await task.join()
    print("[parent] Child exited")


if __name__ == "__main__":
    scheduler = giambio.AsyncScheduler()
    scheduler.start(parent(4, 5))
