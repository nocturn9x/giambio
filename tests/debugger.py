import giambio


class Debugger(giambio.debug.BaseDebugger):
    """
    A simple debugger for giambio
    """

    def on_start(self):
        print("## Started running")

    def on_exit(self):
        print("## Finished running")

    def on_task_schedule(self, task, delay: int):
        print(f">> A task named '{task.name}' was scheduled to run in {delay:.2f} seconds")

    def on_task_spawn(self, task):
        print(f">> A task named '{task.name}' was spawned")

    def on_task_exit(self, task):
        print(f"<< Task '{task.name}' exited")

    def before_task_step(self, task):
        print(f"-> About to run a step for '{task.name}'")

    def after_task_step(self, task):
        print(f"<- Ran a step for '{task.name}'")

    def before_sleep(self, task, seconds):
        print(f"# About to put '{task.name}' to sleep for {seconds:.2f} seconds")

    def after_sleep(self, task, seconds):
        print(f"# Task '{task.name}' slept for {seconds:.2f} seconds")

    def before_io(self, timeout):
        if timeout is None:
            timeout = float("inf")
        print(f"!! About to check for I/O for up to {timeout:.2f} seconds")

    def after_io(self, timeout):
        print(f"!! Done I/O check (waited for {timeout:.2f} seconds)")

    def before_cancel(self, task):
        print(f"// About to cancel '{task.name}'")

    def after_cancel(self, task):
        print(f"// Cancelled '{task.name}'")

    def on_exception_raised(self, task, exc):
        print(f"== '{task.name}' raised {repr(exc)}")
