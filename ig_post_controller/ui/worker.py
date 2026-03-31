from __future__ import annotations

import traceback
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Signal, Slot


class TaskWorker(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, fn, *args, **kwargs) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # pragma: no cover - UI threading path
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.error.emit(details)
        else:
            self.result.emit(result)
        finally:
            self.finished.emit()


class TaskBridge(QObject):
    def __init__(
        self,
        *,
        on_result=None,
        on_error=None,
        on_finished=None,
        on_thread_finished=None,
    ) -> None:
        super().__init__()
        self._on_result = on_result
        self._on_error = on_error
        self._on_finished = on_finished
        self._on_thread_finished = on_thread_finished

    @Slot(object)
    def deliver_result(self, payload) -> None:
        if self._on_result is not None:
            self._on_result(payload)

    @Slot(str)
    def deliver_error(self, message: str) -> None:
        if self._on_error is not None:
            self._on_error(message)

    @Slot()
    def deliver_finished(self) -> None:
        if self._on_finished is not None:
            self._on_finished()

    @Slot()
    def deliver_thread_finished(self) -> None:
        if self._on_thread_finished is not None:
            self._on_thread_finished()


@dataclass(slots=True)
class TaskHandle:
    thread: QThread
    worker: TaskWorker
    bridge: TaskBridge


def create_task_handle(
    fn,
    *args,
    on_result=None,
    on_error=None,
    on_finished=None,
    on_thread_finished=None,
    **kwargs,
) -> TaskHandle:
    thread = QThread()
    worker = TaskWorker(fn, *args, **kwargs)
    bridge = TaskBridge(
        on_result=on_result,
        on_error=on_error,
        on_finished=on_finished,
        on_thread_finished=on_thread_finished,
    )
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.result.connect(bridge.deliver_result)
    worker.error.connect(bridge.deliver_error)
    worker.finished.connect(bridge.deliver_finished)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(bridge.deliver_thread_finished)
    thread.finished.connect(thread.deleteLater)
    return TaskHandle(thread=thread, worker=worker, bridge=bridge)
