"""In-memory task state tracking and async orchestration."""

import asyncio
import uuid
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class TaskPhase(str, Enum):
    UPLOADING = "UPLOADING"
    GENERATING_GOLDENS = "GENERATING_GOLDENS"
    AWAITING_CONFIRM = "AWAITING_CONFIRM"
    RUNNING_EVAL = "RUNNING_EVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskManager:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._events: Dict[str, asyncio.Event] = {}
        self._queues: dict = {}

    def start_task(self, rag_base_url: str, rag_api_key: str) -> str:
        task_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": "UPLOADING",
            "phase": "UPLOADING",
            "progress": 0.0,
            "error_message": None,
            "created_at": now,
            "completed_at": None,
            "rag_base_url": rag_base_url,
            "rag_api_key": rag_api_key,
        }
        return task_id

    def get_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

    def update_phase(
        self,
        task_id: str,
        phase: TaskPhase,
        progress: float = 0.0,
    ) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["phase"] = phase.value
            self._tasks[task_id]["status"] = phase.value
            self._tasks[task_id]["progress"] = progress

    def mark_completed(self, task_id: str) -> None:
        if task_id in self._tasks:
            now = datetime.now(timezone.utc).isoformat()
            self._tasks[task_id]["status"] = "COMPLETED"
            self._tasks[task_id]["phase"] = "COMPLETED"
            self._tasks[task_id]["progress"] = 1.0
            self._tasks[task_id]["completed_at"] = now

    def mark_failed(self, task_id: str, error: str) -> None:
        if task_id in self._tasks:
            now = datetime.now(timezone.utc).isoformat()
            self._tasks[task_id]["status"] = "FAILED"
            self._tasks[task_id]["phase"] = "FAILED"
            self._tasks[task_id]["error_message"] = error
            self._tasks[task_id]["completed_at"] = now

    def set_confirmation_event(self, task_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[task_id] = event
        return event

    def signal_confirmation(self, task_id: str) -> None:
        state = self._tasks.get(task_id)
        if state:
            state["confirmed"] = True
        event = self._events.get(task_id)
        if event:
            event.set()


    def get_queue(self, task_id: str):
        import asyncio
        if task_id not in self._queues:
            self._queues[task_id] = asyncio.Queue()
        return self._queues[task_id]

    async def push_event(self, task_id: str, event: str, data: dict) -> None:
        queue = self.get_queue(task_id)
        await queue.put({"event": event, "data": data})

    def cleanup_queue(self, task_id: str) -> None:
        self._queues.pop(task_id, None)

    def remove_task(self, task_id: str) -> None:
        """Remove in-memory state after a terminal task is deleted."""
        self._tasks.pop(task_id, None)
        self._events.pop(task_id, None)
        self._queues.pop(task_id, None)


# Global singleton
task_manager = TaskManager()
