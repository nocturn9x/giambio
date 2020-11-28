"""
Tooling for debugging giambio

Copyright (C) 2020 nocturn9x

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from abc import ABC, abstractmethod
from giambio.objects import Task


class BaseDebugger(ABC):
   """
   The base for all debugger objects
   """

   @abstractmethod
   def on_start(self):
      """
      This method is called when the event
      loop starts executing
      """

      raise NotImplementedError

   @abstractmethod
   def on_exit(self):
      """
      This method is called when the event
      loop exits entirely (all tasks completed)
      """

      raise NotImplementedError

   @abstractmethod
   def on_task_schedule(self, task: Task, delay: float):
      """
      This method is called when a new task is
      scheduled (not spawned)

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      :param delay: The delay, in seconds, after which
      the task will start executing
      :type delay: float
      """

      raise NotImplementedError

   @abstractmethod
   def on_task_spawn(self, task: Task):
      """
      This method is called when a new task is
      spawned

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      """

      raise NotImplementedError

   @abstractmethod
   def on_task_exit(self, task: Task):
      """
      This method is called when a task exits

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      """

      raise NotImplementedError

   @abstractmethod
   def before_task_step(self, task: Task):
      """
      This method is called right before
      calling a task's run() method

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      """

      raise NotImplementedError

   @abstractmethod
   def after_task_step(self, task: Task):
      """
      This method is called right after
      calling a task's run() method

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      """

      raise NotImplementedError

   @abstractmethod
   def before_sleep(self, task: Task, seconds: float):
      """
      This method is called before a task goes
      to sleep

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      :param seconds: The amount of seconds the
      task wants to sleep
      :type seconds: int
      """

      raise NotImplementedError

   @abstractmethod
   def after_sleep(self, task: Task, seconds: float):
      """
      This method is called after a tasks
      awakes from sleeping

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      :param seconds: The amount of seconds the
      task actually slept
      :type seconds: float
      """

      raise NotImplementedError

   @abstractmethod
   def before_io(self, timeout: float):
      """
      This method is called right before
      the event loop checks for I/O events

      :param timeout: The max. amount of seconds
      that the loop will hang when using the select()
      system call
      :type timeout: float
      """

      raise NotImplementedError

   @abstractmethod
   def after_io(self, timeout: float):
      """
      This method is called right after
      the event loop has checked for I/O events

      :param timeout: The actual amount of seconds
      that the loop has hung when using the select()
      system call
      :type timeout: float
      """

      raise NotImplementedError

   @abstractmethod
   def before_cancel(self, task: Task):
      """
      This method is called right before a task
      gets cancelled

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      """

      raise NotImplementedError

   @abstractmethod
   def after_cancel(self, task: Task):
      """
      This method is called right after a task
      gets cancelled

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      """

      raise NotImplementedError

   @abstractmethod
   def on_exception_raised(self, task: Task, exc: BaseException):
      """
      This method is called right after a task
      has raised an exception

      :param task: The Task object representing a
      giambio Task and wrapping a coroutine
      :type task: :class: giambio.objects.Task
      :param exc: The exception that was raised
      :type exc: BaseException
      """

      raise NotImplementedError

