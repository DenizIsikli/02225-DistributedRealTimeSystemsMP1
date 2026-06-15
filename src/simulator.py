"""
Discrete-Event Simulator for real-time scheduling.

Supports DM and EDF scheduling policies via pluggable policy objects.
Currently only EDF policy is implemented; DM policy is stubbed.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
import heapq
import random
from task_model import Task, TaskSet


# ---------------------------------------------------------------------------
# Event & Job data structures
# ---------------------------------------------------------------------------

class EventType(Enum):
    JOB_RELEASE = 1
    JOB_COMPLETION = 2


@dataclass(order=True)
class Event:
    time: int
    event_type: EventType = field(compare=False)
    task_id: int = field(compare=False)
    job_id: int = field(compare=False)


@dataclass
class Job:
    task_id: int
    job_id: int
    release_time: int
    absolute_deadline: int
    execution_time: int           # Drawn from [BCET, WCET]
    remaining_time: int           # Tracks remaining execution
    last_resume_time: int = -1    # When it last started/resumed executing
    finish_time: int = -1

    @property
    def response_time(self) -> int:
        return self.finish_time - self.release_time


# ---------------------------------------------------------------------------
# Scheduling Policies
# ---------------------------------------------------------------------------

class SchedulingPolicy(ABC):
    @abstractmethod
    def select_job(self, ready_queue: List[Job]) -> Job:
        """Select the highest-priority job from the ready queue."""
        pass

    @abstractmethod
    def name(self) -> str:
        pass


class DMPolicy(SchedulingPolicy):
    """Deadline Monotonic — fixed priority based on relative deadlines."""

    def __init__(self, task_priorities: Dict[int, int]):
        """task_priorities: dict mapping task_id -> priority (lower = higher)"""
        self.priorities = task_priorities

    def select_job(self, ready_queue: List[Job]) -> Job:
        return min(ready_queue, key=lambda j: (self.priorities[j.task_id], j.task_id))

    def name(self) -> str:
        return "DM"


class EDFPolicy(SchedulingPolicy):
    """Earliest Deadline First — dynamic priority based on absolute deadline."""

    def select_job(self, ready_queue: List[Job]) -> Job:
        return min(ready_queue, key=lambda j: (j.absolute_deadline, j.task_id))

    def name(self) -> str:
        return "EDF"


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class Simulator:
    def __init__(self, task_set: TaskSet, policy: SchedulingPolicy,
                 use_wcet: bool = False):
        """
        task_set: the tasks to simulate
        policy: DM or EDF scheduling policy
        use_wcet: if True, always use WCET (for WCRT verification);
                  if False, draw random execution times from [BCET, WCET]
        """
        self.task_set = task_set
        self.policy = policy
        self.use_wcet = use_wcet
        self.event_queue: List[Event] = []   # Min-heap by time
        self.ready_queue: List[Job] = []
        self.running_job: Optional[Job] = None
        self.current_time: int = 0
        self.completed_jobs: List[Job] = []

    def run(self, duration: int = None) -> Dict[int, dict]:
        """
        Run the simulation for 'duration' time units.
        Default: one hyperperiod.

        Returns dict: task_id -> {
            max_response_time, num_jobs, all_response_times, deadline_misses
        }
        """
        if duration is None:
            duration = self.task_set.hyperperiod

        # Initialize: schedule first release for every task at time 0
        for task in self.task_set.tasks:
            heapq.heappush(self.event_queue,
                Event(time=0, event_type=EventType.JOB_RELEASE,
                      task_id=task.id, job_id=0))

        # Main event loop
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > duration:
                break

            self.current_time = event.time

            if event.event_type == EventType.JOB_RELEASE:
                self._handle_release(event)
            elif event.event_type == EventType.JOB_COMPLETION:
                self._handle_completion(event)

        return self._collect_results()

    def _handle_release(self, event: Event):
        task = self._get_task(event.task_id)

        exec_time = task.C if self.use_wcet else random.randint(task.C_best, task.C)
        job = Job(
            task_id=task.id,
            job_id=event.job_id,
            release_time=event.time,
            absolute_deadline=event.time + task.D,
            execution_time=exec_time,
            remaining_time=exec_time
        )
        self.ready_queue.append(job)

        # Schedule next release of this task
        heapq.heappush(self.event_queue,
            Event(time=event.time + task.T, event_type=EventType.JOB_RELEASE,
                  task_id=task.id, job_id=event.job_id + 1))

        self._schedule()

    def _handle_completion(self, event: Event):
        if (self.running_job
                and self.running_job.task_id == event.task_id
                and self.running_job.job_id == event.job_id):
            self.running_job.finish_time = event.time
            self.running_job.remaining_time = 0
            self.completed_jobs.append(self.running_job)
            self.running_job = None

        self._schedule()

    def _schedule(self):
        """Core scheduling decision with preemption support."""
        # Remove completed jobs from ready queue
        self.ready_queue = [j for j in self.ready_queue if j.remaining_time > 0]
        if not self.ready_queue:
            return

        best_job = self.policy.select_job(self.ready_queue)

        if self.running_job is None:
            self._start_job(best_job)
        elif best_job is not self.running_job:
            # *** PREEMPTION ***
            elapsed = self.current_time - self.running_job.last_resume_time
            self.running_job.remaining_time -= elapsed
            self._remove_completion_event(self.running_job)

            # If the preempted job actually just finished (remaining == 0),
            # record it as completed rather than leaving it in limbo.
            if self.running_job.remaining_time <= 0:
                self.running_job.remaining_time = 0
                self.running_job.finish_time = self.current_time
                self.completed_jobs.append(self.running_job)

            self.running_job = None
            # Re-filter ready queue (the just-completed job may need removal)
            self.ready_queue = [j for j in self.ready_queue if j.remaining_time > 0]
            if self.ready_queue:
                self._start_job(self.policy.select_job(self.ready_queue))

    def _start_job(self, job: Job):
        self.running_job = job
        job.last_resume_time = self.current_time

        heapq.heappush(self.event_queue,
            Event(time=self.current_time + job.remaining_time,
                  event_type=EventType.JOB_COMPLETION,
                  task_id=job.task_id, job_id=job.job_id))

    def _remove_completion_event(self, job: Job):
        """Remove the stale completion event for a preempted job."""
        self.event_queue = [
            e for e in self.event_queue
            if not (e.event_type == EventType.JOB_COMPLETION
                    and e.task_id == job.task_id
                    and e.job_id == job.job_id)
        ]
        heapq.heapify(self.event_queue)

    def _get_task(self, task_id: int) -> Task:
        for t in self.task_set.tasks:
            if t.id == task_id:
                return t
        raise ValueError(f"Task {task_id} not found")

    def _collect_results(self) -> Dict[int, dict]:
        """Compute per-task statistics from completed jobs."""
        results = {}
        for task in self.task_set.tasks:
            task_jobs = [j for j in self.completed_jobs if j.task_id == task.id]
            if task_jobs:
                rts = [j.response_time for j in task_jobs]
                results[task.id] = {
                    'max_response_time': max(rts),
                    'num_jobs': len(task_jobs),
                    'all_response_times': rts,
                    'deadline_misses': sum(1 for rt in rts if rt > task.D)
                }
            else:
                results[task.id] = {
                    'max_response_time': None,
                    'num_jobs': 0,
                    'all_response_times': [],
                    'deadline_misses': 0
                }
        return results
