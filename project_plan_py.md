# DRTS Mini-Project 1 — Complete Coding Guide (Python)

## Table of Contents

1. [Project Architecture](#1-project-architecture)
2. [Data Model](#2-data-model)
3. [Module 1: DM Scheduling Analysis](#3-module-1-dm-scheduling-analysis)
4. [Module 2: EDF Scheduling Analysis](#4-module-2-edf-scheduling-analysis)
5. [Module 3: Discrete-Event Simulator](#5-module-3-discrete-event-simulator)
6. [Module 4: CSV Loader & Test Case Generation](#6-module-4-csv-loader--test-case-generation)
7. [Module 5: Comparison & Visualization](#7-module-5-comparison--visualization)
8. [Pseudocode for All Core Algorithms](#8-pseudocode-for-all-core-algorithms)
9. [Validation Strategy](#9-validation-strategy)
10. [Common Pitfalls & Debugging](#10-common-pitfalls--debugging)

---

## 1. Project Architecture

```
mini-project-1-RTDS/
├── main.py                  # Entry point: orchestrates analysis + simulation + comparison
├── task_model.py            # Task and TaskSet data structures
├── dm_analysis.py           # Deadline Monotonic WCRT analysis
├── edf_analysis.py          # EDF schedulability test + WCRT computation
├── simulator.py             # Discrete-event simulator (supports DM & EDF)
├── csv_loader.py            # Parse provided CSV task sets from output/
├── task_generator.py        # UUniFast + random task set generation
├── comparator.py            # Runs experiments, collects results
├── plotter.py               # All matplotlib visualization code
├── test_cases.py            # Predefined Buttazzo test task sets
├── tests/
│   ├── test_dm.py           # Unit tests for DM analysis
│   ├── test_edf.py          # Unit tests for EDF analysis
│   └── test_simulator.py    # Unit tests for simulator
├── output/                  # Pre-generated test data (provided)
│   ├── automotive-utilDist/...
│   └── uunifast-utilDist/...
├── results/                 # Output plots and CSV results
├── project_plan_py.md       # This file
├── requirements.txt         # numpy, matplotlib, pandas
└── task_desc.txt
```

### Dependencies (`requirements.txt`)

```
numpy
matplotlib
pandas
```

Install: `pip install -r requirements.txt`

All three are standard and sufficient. No specialized real-time libraries needed.

---

## 2. Data Model

### 2.1 Task Definition

Each periodic task τ_i is described by:

| Parameter | Symbol | Field | Type  | Description |
|-----------|--------|-------|-------|-------------|
| ID        | `id`   | `id`  | `int` | Unique task identifier |
| Period    | `T`    | `T`   | `int` | Time between successive releases |
| WCET      | `C`    | `C`   | `int` | Worst-Case Execution Time |
| BCET      | `C_best`| `C_best`| `int` | Best-Case Execution Time (for simulation) |
| Deadline  | `D`    | `D`   | `int` | Relative deadline, where D ≤ T |
| Priority  | `priority`| `priority`| `int` | Assigned by scheduler (lower number = higher priority) |

### 2.2 Python Implementation

```python
# task_model.py

from dataclasses import dataclass
from typing import List
import math
from functools import reduce

MAX_HYPERPERIOD = 100_000_000  # Safety cap to prevent OOM

@dataclass
class Task:
    id: int
    T: int          # Period
    C: int          # WCET
    D: int          # Relative deadline (D <= T)
    C_best: int = 0 # BCET (defaults to 0, set to C for worst-case simulation)
    priority: int = 0  # Assigned by scheduler

    def __post_init__(self):
        if self.C_best == 0:
            self.C_best = self.C  # Default BCET = WCET
        assert self.D <= self.T, f"Task {self.id}: D={self.D} must be <= T={self.T}"
        assert self.C_best <= self.C, f"Task {self.id}: BCET must be <= WCET"
        assert self.C <= self.D, f"Task {self.id}: C={self.C} must be <= D={self.D}"

    def utilization(self) -> float:
        return self.C / self.T

    def __repr__(self):
        return f"τ{self.id}(T={self.T}, C={self.C}, D={self.D}, BCET={self.C_best})"


@dataclass
class TaskSet:
    tasks: List[Task]

    @property
    def utilization(self) -> float:
        """Total utilization U = Σ(C_i / T_i)"""
        return sum(t.C / t.T for t in self.tasks)

    @property
    def hyperperiod(self) -> int:
        """LCM of all periods. Capped at MAX_HYPERPERIOD to avoid OOM."""
        lcm = reduce(math.lcm, [t.T for t in self.tasks])
        return min(lcm, MAX_HYPERPERIOD)

    def is_feasible(self) -> bool:
        """Necessary condition: U <= 1"""
        return self.utilization <= 1.0

    def density(self) -> float:
        """Σ(C_i / D_i) — tighter necessary condition for constrained deadlines"""
        return sum(t.C / t.D for t in self.tasks)

    def all_implicit_deadlines(self) -> bool:
        """Whether all tasks have D == T"""
        return all(t.D == t.T for t in self.tasks)

    def size(self) -> int:
        return len(self.tasks)
```

### 2.3 Utility Function

```python
def int_ceil_div(a: int, b: int) -> int:
    """Integer ceiling division: ⌈a/b⌉ without floating-point errors."""
    return (a + b - 1) // b
```

### 2.4 Design Decisions

- **Use integers for all time values.** Python has arbitrary-precision integers, so no overflow risk. But floating-point `math.ceil(R / T)` still introduces rounding errors in ceiling operations — use the integer trick.
- **Store BCET alongside WCET** so the simulator can draw random execution times from [BCET, WCET].
- **Priority is mutable** — it gets assigned by the scheduling algorithm (DM assigns it, EDF changes it dynamically).
- **Hyperperiod cap** at 10⁸ prevents OOM in the simulator. The provided automotive CSVs have periods up to 10⁷.

---

## 3. Module 1: DM Scheduling Analysis

### 3.1 Priority Assignment

Deadline Monotonic assigns priorities by **relative deadline**: shorter deadline → higher priority.

### 3.2 WCRT Computation — Fixed-Point Iteration

The WCRT for task τ_i under fixed-priority scheduling is:

```
R_i = C_i + Σ_{j ∈ hp(i)} ⌈R_i / T_j⌉ · C_j
```

This is solved iteratively:

```
R_i^(0) = C_i
R_i^(n+1) = C_i + Σ_{j ∈ hp(i)} ⌈R_i^(n) / T_j⌉ · C_j
```

**Termination conditions:**
1. **Converged:** R_i^(n+1) = R_i^(n) → WCRT found
2. **Unschedulable:** R_i^(n+1) > D_i → task misses deadline

### 3.3 Full Implementation

```python
# dm_analysis.py

from task_model import Task, TaskSet, int_ceil_div
from typing import Dict, Tuple


def assign_dm_priorities(task_set: TaskSet) -> None:
    """Assign DM priorities: shorter deadline = higher priority (lower number)."""
    sorted_tasks = sorted(task_set.tasks, key=lambda t: (t.D, t.id))
    for priority, task in enumerate(sorted_tasks):
        task.priority = priority


def compute_dm_wcrt(task_set: TaskSet) -> Dict[int, Tuple[int, bool]]:
    """
    Compute WCRT for each task under DM scheduling.

    Returns:
        dict mapping task_id -> (wcrt, schedulable)
    """
    assign_dm_priorities(task_set)
    sorted_tasks = sorted(task_set.tasks, key=lambda t: t.priority)
    results = {}

    for i, task_i in enumerate(sorted_tasks):
        # hp(i) = all tasks with higher priority (lower priority number)
        higher_priority = sorted_tasks[:i]

        # Initial value
        R = task_i.C
        schedulable = True

        while True:
            # Compute next iteration
            R_new = task_i.C
            for task_j in higher_priority:
                R_new += int_ceil_div(R, task_j.T) * task_j.C

            if R_new == R:
                # Converged
                break
            if R_new > task_i.D:
                # Exceeded deadline — unschedulable
                schedulable = False
                R = R_new
                break
            R = R_new

        results[task_i.id] = (R, schedulable and (R <= task_i.D))

    return results


def is_dm_schedulable(task_set: TaskSet) -> bool:
    """Convenience: is the entire task set schedulable under DM?"""
    return all(sched for _, sched in compute_dm_wcrt(task_set).values())
```

### 3.4 Key Considerations

- **The iteration always terminates** because either R converges (non-decreasing and bounded) or exceeds D_i.
- **Ceiling function pitfall:** `math.ceil(R / T)` can be wrong due to float division. Use the integer ceiling trick: `(R + T - 1) // T`.
- **The highest-priority task** always has WCRT = C_i (no interference).

---

## 4. Module 2: EDF Scheduling Analysis

### 4.1 Schedulability — Processor Demand Approach

For constrained deadlines (D_i ≤ T_i), a task set is schedulable under EDF if and only if:

```
∀L ∈ D: h(L) ≤ L
```

where:

```
h(L) = Σ_{i: D_i ≤ L} (⌊(L - D_i) / T_i⌋ + 1) · C_i
```

and D is the set of absolute deadlines within [0, L*], where L* is the upper bound.

### 4.2 Computing the Testing Points

The set of testing points D consists of:

```
d_{i,k} = D_i + k · T_i    for k = 0, 1, 2, ...
```

up to an upper bound L*.

**Computing L* (Busy Period Bound) — iterative approach:**

```
L^(0) = Σ C_i
L^(n+1) = Σ ⌊(L^(n) + T_i - D_i) / T_i⌋ · C_i
```

Iterate until convergence or exceed a maximum bound.

### 4.3 Full Implementation

```python
# edf_analysis.py

from task_model import Task, TaskSet
from typing import List, Dict, Tuple


def compute_demand(tasks: List[Task], L: int) -> int:
    """
    Processor demand h(L): total execution time demanded in [0, L]
    by all jobs with both release and deadline within [0, L].
    """
    demand = 0
    for t in tasks:
        if t.D <= L:
            num_jobs = (L - t.D) // t.T + 1  # ⌊(L - D_i) / T_i⌋ + 1
            demand += num_jobs * t.C
    return demand


def compute_L_star(task_set: TaskSet) -> int:
    """Compute the upper bound for testing points using iterative method.
    Returns -1 if U >= 1 (unschedulable)."""
    if task_set.utilization >= 1.0:
        return -1

    tasks = task_set.tasks
    L = sum(t.C for t in tasks)
    max_L = task_set.hyperperiod  # Never need to check beyond hyperperiod
    max_iter = 1000

    for _ in range(max_iter):
        L_new = sum(((L + t.T - t.D) // t.T) * t.C for t in tasks)
        if L_new == L:
            return L
        if L_new > max_L:
            return max_L
        L = L_new

    return L


def get_testing_points(task_set: TaskSet, L_star: int) -> List[int]:
    """Generate all absolute deadline points d_{i,k} = D_i + k*T_i up to L*."""
    points = set()
    for t in task_set.tasks:
        d = t.D
        while d <= L_star:
            points.add(d)
            d += t.T
    return sorted(points)


def edf_schedulability_test(task_set: TaskSet) -> bool:
    """
    Test if the task set is schedulable under EDF using the
    Processor Demand Approach.
    """
    U = task_set.utilization
    if U > 1.0:
        return False

    # For D_i == T_i for all tasks, U <= 1 is sufficient
    if task_set.all_implicit_deadlines():
        return True

    L_star = compute_L_star(task_set)
    if L_star == -1:
        return False

    testing_points = get_testing_points(task_set, L_star)

    for L in testing_points:
        if compute_demand(task_set.tasks, L) > L:
            return False
    return True
```

### 4.4 EDF WCRT Computation

Computing the exact WCRT under EDF for constrained deadlines is more complex than DM. The approach:

For each task τ_i, find the maximum response time across all possible job releases. Under synchronous release (worst case), compute when each job of τ_i finishes.

**Approach — Iterative over a busy period:**

```python
def compute_edf_wcrt(task_set: TaskSet) -> Dict[int, Tuple[int, bool]]:
    """
    Compute WCRT for each task under EDF.
    Returns dict: task_id -> (wcrt, schedulable)
    """
    tasks = task_set.tasks
    results = {}
    L_star = compute_L_star(task_set)
    if L_star == -1:
        L_star = task_set.hyperperiod

    for task_i in tasks:
        max_response = 0

        k = 0
        while True:
            release_time = k * task_i.T
            if release_time >= L_star:
                break

            finish_time = _compute_edf_job_finish(tasks, task_i, k, L_star)
            response = finish_time - release_time
            max_response = max(max_response, response)
            k += 1

        results[task_i.id] = (max_response, max_response <= task_i.D)

    return results


def _compute_edf_job_finish(tasks: List[Task], target: Task, job_index: int,
                             L_star: int) -> int:
    """
    Compute the finish time of the job_index-th job of 'target' task
    under EDF scheduling with synchronous release at time 0.
    Uses iterative fixed-point computation.
    """
    release = job_index * target.T
    abs_deadline = release + target.D

    def workload(t):
        w = 0
        for task in tasks:
            if task.id == target.id:
                jobs = min(job_index + 1, t // task.T + 1 if t >= 0 else 0)
                w += jobs * task.C
            else:
                if abs_deadline < task.D:
                    continue
                max_k_deadline = (abs_deadline - task.D) // task.T
                max_k_released = t // task.T if t >= 0 else -1
                jobs = min(max_k_deadline, max_k_released) + 1
                if jobs > 0:
                    w += jobs * task.C
        return w

    t = workload(0)
    for _ in range(10_000):
        t_new = workload(t)
        if t_new == t:
            return t
        if t_new > L_star * 2:
            return t_new  # Diverging — unschedulable
        t = t_new

    return t
```

### 4.5 Key Challenges

1. **EDF WCRT has no simple closed-form.** The iterative approach above considers each job instance and computes interference from all jobs with earlier or equal absolute deadlines.
2. **The busy period bound** must be computed carefully to avoid infinite loops.
3. **An alternative approach:** If EDF WCRT is too complex analytically, **use the simulator as the primary EDF WCRT measurement tool** (running with all execution times set to WCET). This is a valid and common approach for the project.

---

## 5. Module 3: Discrete-Event Simulator

This is the **most complex coding component**.

### 5.1 Architecture

```
Simulator
├── Event Queue (heapq priority queue sorted by time)
│   ├── JOB_RELEASE events
│   ├── JOB_COMPLETION events
│   └── (implicit: PREEMPTION via re-evaluation at release)
├── Ready Queue (list, sorted by policy on selection)
├── Scheduler (SchedulingPolicy: DM or EDF, pluggable)
└── Statistics Collector (response times, deadline misses)
```

### 5.2 Event & Job Classes

```python
# simulator.py

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import heapq
import random
from task_model import Task, TaskSet


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
```

### 5.3 Scheduling Policy Interface

```python
from abc import ABC, abstractmethod


class SchedulingPolicy(ABC):
    @abstractmethod
    def select_job(self, ready_queue: List[Job]) -> Job:
        """Select the highest-priority job from the ready queue."""
        pass

    @abstractmethod
    def name(self) -> str:
        pass


class DMPolicy(SchedulingPolicy):
    def __init__(self, task_priorities: Dict[int, int]):
        """task_priorities: dict mapping task_id -> priority (lower = higher)"""
        self.priorities = task_priorities

    def select_job(self, ready_queue: List[Job]) -> Job:
        return min(ready_queue, key=lambda j: (self.priorities[j.task_id], j.task_id))

    def name(self) -> str:
        return "DM"


class EDFPolicy(SchedulingPolicy):
    def select_job(self, ready_queue: List[Job]) -> Job:
        return min(ready_queue, key=lambda j: (j.absolute_deadline, j.task_id))

    def name(self) -> str:
        return "EDF"
```

### 5.4 Simulator Core

```python
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
        Returns dict: task_id -> {max_response_time, num_jobs, all_response_times, deadline_misses}
        """
        if duration is None:
            duration = self.task_set.hyperperiod

        # Initialize: schedule first release for every task at time 0
        for task in self.task_set.tasks:
            heapq.heappush(self.event_queue,
                Event(time=0, event_type=EventType.JOB_RELEASE,
                      task_id=task.id, job_id=0))

        # Main loop
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

        # Schedule next release
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
        """Core scheduling decision with preemption."""
        # Remove completed jobs
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
            self.running_job = None
            self._start_job(best_job)

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
        """Compute per-task maximum observed response time."""
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
```

### 5.5 Critical Implementation Details

#### 5.5.1 Preemption Handling

This is the **#1 source of bugs**. When a new job arrives and has higher priority than the running job:

1. Compute how much time the running job has already used since it last started/resumed.
2. Subtract from `remaining_time`.
3. Remove the stale completion event from the event queue.
4. Start the new higher-priority job.
5. The preempted job stays in the ready queue with updated `remaining_time`.

**Bug to avoid:** The field must track the **last resume time** (`last_resume_time`), not the original release. If you mix these up, remaining time calculations will be wrong.

#### 5.5.2 Event Queue Consistency

When you preempt a job, its old completion event is now invalid. You **must** remove it. Two approaches:

1. **Lazy deletion:** Mark events as invalid and skip them when popped. More efficient for large simulations.
2. **Eager deletion:** Filter the list and re-heapify (as shown above). Simpler but O(n) per preemption.

For this project, eager deletion is fine — task sets are small (≤46 tasks).

#### 5.5.3 Tie-Breaking

When two jobs have the same priority (DM) or same deadline (EDF), define a consistent tie-breaking rule:
- **DM:** Break ties by task ID (lower ID wins) — see `key=lambda j: (priority, j.task_id)`.
- **EDF:** Break ties by task ID — see `key=lambda j: (j.absolute_deadline, j.task_id)`.

Without consistent tie-breaking, results become non-deterministic.

#### 5.5.4 Simulation Duration

- **Minimum:** One hyperperiod (LCM of all periods).
- **For random execution times:** Run multiple hyperperiods (e.g., 10×) or multiple independent runs to observe a distribution.
- **For WCRT verification:** Run with `use_wcet=True` for at least one hyperperiod. The maximum observed response time should equal (or very closely match) the analytical WCRT.

---

## 6. Module 4: CSV Loader & Test Case Generation

### 6.1 CSV Loader — Loading Provided Test Data

The `output/` directory contains pre-generated task sets. CSV format:

```
TaskID,Jitter,BCET,WCET,Period,Deadline,PE
0,0,170,1700,50000,50000,0
1,0,95,950,100000,100000,0
...
```

**Notes on the data:**
- Jitter is always 0 — ignored.
- PE (processing element) is always 0 — ignored (single core).
- BCET ≈ WCET/10 in most files.
- All provided CSVs have **D == T** (implicit deadlines).
- Automotive sets have variable task counts (17–46); UUniFast sets have exactly 25 tasks.

```python
# csv_loader.py

import csv
from pathlib import Path
from typing import Dict, List
from task_model import Task, TaskSet


def load_taskset(csv_path: Path) -> TaskSet:
    """
    Load a single CSV file into a TaskSet.
    Expected header: TaskID,Jitter,BCET,WCET,Period,Deadline,PE
    """
    tasks = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            bcet = max(1, int(row['BCET']))   # Guard against BCET=0
            tasks.append(Task(
                id=int(row['TaskID']),
                T=int(row['Period']),
                C=int(row['WCET']),
                D=int(row['Deadline']),
                C_best=bcet
            ))
    return TaskSet(tasks)


def load_all_util_levels(base_path: Path) -> Dict[float, List[TaskSet]]:
    """
    Load all task sets for a given utilization distribution path.
    E.g., "output/automotive-utilDist/automotive-perDist/1-core/25-task/0-jitter"
    Returns dict: utilization (e.g. 0.10) -> list of TaskSets.
    """
    result = {}
    for util_dir in sorted(base_path.iterdir()):
        if not util_dir.is_dir():
            continue
        # Parse "0.50-util" -> 0.50
        util = float(util_dir.name.replace('-util', ''))

        tasksets_dir = util_dir / 'tasksets'
        if not tasksets_dir.is_dir():
            continue

        sets = []
        for csv_file in sorted(tasksets_dir.glob('*.csv')):
            sets.append(load_taskset(csv_file))

        result[util] = sets

    return result
```

### 6.2 UUniFast Algorithm

Generates n utilization values that sum to a target U:

```python
# task_generator.py

import random
from typing import List
from task_model import Task, TaskSet


def uunifast(n: int, U_total: float) -> List[float]:
    """
    UUniFast algorithm for generating n utilization values
    summing to U_total, uniformly distributed.
    """
    utilizations = []
    sum_U = U_total

    for i in range(1, n):
        next_sum = sum_U * random.random() ** (1.0 / (n - i))
        utilizations.append(sum_U - next_sum)
        sum_U = next_sum

    utilizations.append(sum_U)
    return utilizations


def generate_task_set(
    n: int,
    U_total: float,
    period_range: tuple = (10, 100),
    deadline_factor_range: tuple = (0.5, 1.0)
) -> TaskSet:
    """
    Generate a random task set with n tasks and total utilization U_total.
    deadline_factor_range: D_i = factor * T_i, where factor in [0.5, 1.0]
    """
    utilizations = uunifast(n, U_total)
    tasks = []

    for i, u_i in enumerate(utilizations):
        T = random.randint(*period_range)
        C = max(1, int(round(u_i * T)))
        factor = random.uniform(*deadline_factor_range)
        D = max(C, int(round(factor * T)))
        D = min(D, T)
        tasks.append(Task(id=i, T=T, C=C, D=D, C_best=max(1, C // 2)))

    return TaskSet(tasks)


def generate_implicit_deadline_set(n: int, U_total: float,
                                    period_range: tuple = (10, 100)) -> TaskSet:
    """Convenience: generate with D = T."""
    return generate_task_set(n, U_total, period_range, (1.0, 1.0))
```

### 6.3 Known Test Cases (for Validation)

```python
# test_cases.py

from task_model import Task, TaskSet


def buttazzo_example() -> TaskSet:
    """Buttazzo Example (Section 4.5)"""
    return TaskSet([
        Task(id=1, T=10, C=3, D=7),
        Task(id=2, T=15, C=4, D=15),
        Task(id=3, T=20, C=2, D=20),
    ])


def harmonic_periods() -> TaskSet:
    """Simple harmonic periods"""
    return TaskSet([
        Task(id=1, T=4,  C=1, D=4),
        Task(id=2, T=8,  C=2, D=8),
        Task(id=3, T=16, C=3, D=16),
    ])


def tight_utilization() -> TaskSet:
    """Tight utilization — DM fails, EDF succeeds"""
    return TaskSet([
        Task(id=1, T=6,  C=2, D=5),
        Task(id=2, T=8,  C=2, D=6),
        Task(id=3, T=12, C=3, D=12),
    ])
```

---

## 7. Module 5: Comparison & Visualization

### 7.1 Experiment 1: Schedulability Ratio vs. Utilization (Using Provided Test Data)

```python
# comparator.py

from pathlib import Path
from typing import Dict, List
import numpy as np
from csv_loader import load_all_util_levels
from dm_analysis import compute_dm_wcrt, is_dm_schedulable
from edf_analysis import edf_schedulability_test
from task_model import TaskSet


def experiment_schedulability_from_data(base_path: Path) -> Dict[float, dict]:
    """
    For each utilization level in the provided data, compute the fraction
    of task sets schedulable under DM vs. EDF.
    Returns dict: util -> {'dm_ratio': float, 'edf_ratio': float, 'count': int}
    """
    data = load_all_util_levels(base_path)
    results = {}

    for util, sets in sorted(data.items()):
        dm_count = sum(1 for ts in sets if is_dm_schedulable(ts))
        edf_count = sum(1 for ts in sets if edf_schedulability_test(ts))

        results[util] = {
            'dm_ratio': dm_count / len(sets),
            'edf_ratio': edf_count / len(sets),
            'count': len(sets)
        }

    return results
```

### 7.2 Experiment 2: Schedulability Ratio (Generated Task Sets)

```python
from task_generator import generate_task_set

def experiment_schedulability_generated(
    n_tasks: int = 4,
    utilization_range=np.arange(0.1, 1.05, 0.05),
    num_task_sets: int = 1000
) -> dict:
    """Generate random task sets and compute DM vs EDF schedulability."""
    dm_ratios = []
    edf_ratios = []

    for U in utilization_range:
        dm_count = 0
        edf_count = 0

        for _ in range(num_task_sets):
            ts = generate_task_set(n_tasks, U)
            if is_dm_schedulable(ts):
                dm_count += 1
            if edf_schedulability_test(ts):
                edf_count += 1

        dm_ratios.append(dm_count / num_task_sets)
        edf_ratios.append(edf_count / num_task_sets)

    return {
        'utilizations': list(utilization_range),
        'dm_ratios': dm_ratios,
        'edf_ratios': edf_ratios
    }
```

### 7.3 Experiment 3: Analytical WCRT vs. Simulated Max Response Time

```python
from simulator import Simulator, DMPolicy, EDFPolicy

def experiment_wcrt_comparison(task_set: TaskSet):
    """Compare analytical WCRT with simulated response times."""
    dm_wcrt = compute_dm_wcrt(task_set)
    from edf_analysis import compute_edf_wcrt
    edf_wcrt = compute_edf_wcrt(task_set)

    priorities = {t.id: t.priority for t in task_set.tasks}

    dm_sim = Simulator(task_set, DMPolicy(priorities), use_wcet=True).run()
    edf_sim = Simulator(task_set, EDFPolicy(), use_wcet=True).run()

    print(f"{'Task':<6} {'DM WCRT':<10} {'DM Sim':<10} {'EDF WCRT':<10} {'EDF Sim':<10}")
    print("-" * 50)
    for task in task_set.tasks:
        tid = task.id
        print(f"{tid:<6} "
              f"{dm_wcrt[tid][0]:<10} "
              f"{dm_sim[tid]['max_response_time']:<10} "
              f"{edf_wcrt[tid][0]:<10} "
              f"{edf_sim[tid]['max_response_time']:<10}")
```

### 7.4 Experiment 4: Response Time Distribution (Random Execution Times)

```python
def experiment_rt_distribution(task_set: TaskSet, num_runs: int = 100) -> dict:
    """
    Run simulation many times with random execution times.
    Returns per-task response time lists and analytical WCRTs.
    """
    dm_wcrt = compute_dm_wcrt(task_set)
    priorities = {t.id: t.priority for t in task_set.tasks}

    all_rts = {t.id: [] for t in task_set.tasks}

    duration = task_set.hyperperiod * 5
    for _ in range(num_runs):
        sim = Simulator(task_set, DMPolicy(priorities), use_wcet=False)
        results = sim.run(duration=duration)
        for task in task_set.tasks:
            all_rts[task.id].extend(results[task.id]['all_response_times'])

    return {
        'response_times': all_rts,
        'wcrts': {tid: wcrt for tid, (wcrt, _) in dm_wcrt.items()},
        'deadlines': {t.id: t.D for t in task_set.tasks}
    }
```

### 7.5 Plotting

```python
# plotter.py

import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List


def plot_schedulability(results: dict, title: str = "DM vs EDF Schedulability",
                        save_path: str = None):
    """Plot schedulability ratio vs utilization."""
    utils = results['utilizations']
    plt.figure(figsize=(10, 6))
    plt.plot(utils, results['dm_ratios'], 'b-o', label='DM', markersize=5)
    plt.plot(utils, results['edf_ratios'], 'r-s', label='EDF', markersize=5)
    plt.xlabel('Total Utilization')
    plt.ylabel('Schedulability Ratio')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_schedulability_from_data(results: Dict[float, dict],
                                   title: str = "DM vs EDF Schedulability (Provided Data)",
                                   save_path: str = None):
    """Plot schedulability from pre-generated test data."""
    utils = sorted(results.keys())
    dm_ratios = [results[u]['dm_ratio'] for u in utils]
    edf_ratios = [results[u]['edf_ratio'] for u in utils]

    plt.figure(figsize=(10, 6))
    plt.plot(utils, dm_ratios, 'b-o', label='DM', markersize=5)
    plt.plot(utils, edf_ratios, 'r-s', label='EDF', markersize=5)
    plt.xlabel('Total Utilization')
    plt.ylabel('Schedulability Ratio')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_wcrt_comparison(task_set, dm_wcrt, dm_sim, edf_wcrt, edf_sim,
                          save_path: str = None):
    """Bar chart: analytical vs simulated WCRT per task."""
    task_ids = [t.id for t in task_set.tasks]
    x = np.arange(len(task_ids))
    width = 0.2

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - 1.5*width, [dm_wcrt[tid][0] for tid in task_ids], width, label='DM Analytical')
    ax.bar(x - 0.5*width, [dm_sim[tid]['max_response_time'] for tid in task_ids], width, label='DM Simulated')
    ax.bar(x + 0.5*width, [edf_wcrt[tid][0] for tid in task_ids], width, label='EDF Analytical')
    ax.bar(x + 1.5*width, [edf_sim[tid]['max_response_time'] for tid in task_ids], width, label='EDF Simulated')

    ax.set_xlabel('Task ID')
    ax.set_ylabel('Response Time')
    ax.set_title('Analytical WCRT vs Simulated Max Response Time')
    ax.set_xticks(x)
    ax.set_xticklabels(task_ids)
    ax.legend()
    ax.grid(True, axis='y')
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_rt_distribution(rt_data: dict, save_path: str = None):
    """Histogram of observed response times with WCRT and deadline markers."""
    task_ids = sorted(rt_data['response_times'].keys())
    n = len(task_ids)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4))
    if n == 1:
        axes = [axes]

    for ax, tid in zip(axes, task_ids):
        rts = rt_data['response_times'][tid]
        wcrt = rt_data['wcrts'][tid]
        deadline = rt_data['deadlines'][tid]

        ax.hist(rts, bins=30, alpha=0.7, label='Observed')
        ax.axvline(x=wcrt, color='r', linestyle='--', linewidth=2,
                   label=f'WCRT={wcrt}')
        ax.axvline(x=deadline, color='g', linestyle=':', linewidth=2,
                   label=f'Deadline={deadline}')
        ax.set_xlabel('Response Time')
        ax.set_ylabel('Count')
        ax.set_title(f'Task {tid}')
        ax.legend(fontsize=8)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
```

### 7.6 Expected Plots Summary

| Plot | What it shows | X-axis | Y-axis |
|------|--------------|--------|--------|
| Schedulability ratio | DM vs EDF across utilizations | Utilization (0–1) | Fraction schedulable |
| WCRT bar chart | Analytical vs simulated per task | Task ID | Response time |
| RT distribution | Histogram of observed RTs with WCRT bound | Response time | Count |
| Timeline / Gantt | Execution timeline showing preemptions | Time | Task ID |

---

## 8. Pseudocode for All Core Algorithms

### 8.1 DM WCRT (Algorithm from Buttazzo Fig. 4.17)

```
FUNCTION DM_WCRT(TaskSet Γ):
    Sort Γ by deadline (ascending) → assign priorities
    FOR each task τ_i in priority order:
        R ← C_i
        REPEAT:
            R_new ← C_i + Σ_{j ∈ hp(i)} ⌈R / T_j⌉ · C_j
            IF R_new == R:
                RETURN R as WCRT of τ_i
            IF R_new > D_i:
                RETURN "unschedulable"
            R ← R_new
```

### 8.2 EDF Processor Demand Test

```
FUNCTION EDF_Demand_Test(TaskSet Γ):
    IF Σ(C_i/T_i) > 1: RETURN "unschedulable"
    IF ∀i: D_i == T_i: RETURN "schedulable"
    Compute L* (busy period bound)
    Generate testing points D = {D_i + k·T_i | k≥0, D_i + k·T_i ≤ L*}
    FOR each L in sorted(D):
        h ← Σ_{D_i ≤ L} (⌊(L-D_i)/T_i⌋ + 1) · C_i
        IF h > L: RETURN "unschedulable"
    RETURN "schedulable"
```

### 8.3 Simulator Main Loop

```
FUNCTION Simulate(TaskSet Γ, Policy π, Duration T):
    EventQueue ← release events for all tasks at time 0
    ReadyQueue ← ∅
    RunningJob ← NULL

    WHILE EventQueue not empty AND time ≤ T:
        event ← pop earliest event
        current_time ← event.time

        IF event is JOB_RELEASE:
            Create job with execution time in [BCET, WCET]
            Add job to ReadyQueue
            Schedule next release at current_time + T_i
            Call SCHEDULE()

        IF event is JOB_COMPLETION:
            Record response time = current_time - release_time
            RunningJob ← NULL
            Call SCHEDULE()

    FUNCTION SCHEDULE():
        best ← π.select(ReadyQueue)
        IF RunningJob is NULL:
            Start best
        ELSE IF best ≠ RunningJob:
            Preempt RunningJob (update remaining time, remove old completion)
            Start best
```

---

## 9. Validation Strategy

### Step 1: Unit Test the DM Analysis

```python
# tests/test_dm.py

from test_cases import buttazzo_example
from dm_analysis import compute_dm_wcrt

def test_buttazzo_example():
    ts = buttazzo_example()
    results = compute_dm_wcrt(ts)
    # τ1(D=7): R1 = 3 (highest priority, no interference)
    assert results[1] == (3, True)
    # Hand-compute τ2 and τ3 WCRTs and assert
    assert results[2][1] == True   # schedulable
    assert results[3][1] == True   # schedulable
```

### Step 2: Unit Test the EDF Analysis

```python
# tests/test_edf.py

from test_cases import buttazzo_example, tight_utilization
from edf_analysis import edf_schedulability_test
from dm_analysis import is_dm_schedulable

def test_edf_schedulability():
    assert edf_schedulability_test(buttazzo_example()) == True
    assert edf_schedulability_test(tight_utilization()) == True
    # DM should FAIL on tight_utilization, EDF should PASS
    assert is_dm_schedulable(tight_utilization()) == False
```

### Step 3: Cross-Validate Simulator Against Analysis

```python
# tests/test_simulator.py

from test_cases import buttazzo_example
from dm_analysis import compute_dm_wcrt
from simulator import Simulator, DMPolicy

def test_simulator_matches_analysis():
    ts = buttazzo_example()
    analytical = compute_dm_wcrt(ts)
    priorities = {t.id: t.priority for t in ts.tasks}

    sim_results = Simulator(ts, DMPolicy(priorities), use_wcet=True).run()

    for task in ts.tasks:
        assert sim_results[task.id]['max_response_time'] == analytical[task.id][0], \
            f"WCRT mismatch for task {task.id}"
```

### Step 4: Sanity Checks
- A task set with U > 1 should be unschedulable under both DM and EDF.
- A single task should have WCRT = C.
- With only one task, DM and EDF should give identical results.

---

## 10. Common Pitfalls & Debugging

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Float ceiling | WCRT off by 1 | Use `(a + b - 1) // b` integer arithmetic, never `math.ceil(a / b)` |
| Stale completion events | Jobs "complete" at wrong time after preemption | Always remove old completion event on preempt |
| Wrong remaining time | Negative remaining time or bloated response | Track `last_resume_time`, not `release_time` |
| Hyperperiod overflow | Simulation runs forever or OOM | Cap at `MAX_HYPERPERIOD = 100_000_000` |
| EDF tie-breaking | Non-deterministic results | Use task ID as secondary sort key |
| Off-by-one in demand | h(L) is 1 job too many or too few | Verify with hand computation: job count at boundary |
| Simulation too short | Max observed RT < analytical WCRT | Ensure synchronous release at t=0 in WCET mode |
| Priority inversion in DM | Wrong task runs first | Double-check: lower priority NUMBER = higher priority |

---

## Summary of Effort by Module

| Module | Difficulty | Approx. Lines | Dependencies |
|--------|-----------|---------------|--------------|
| Task Model | Easy | ~60 | None |
| CSV Loader | Easy | ~50 | Task Model |
| DM Analysis | Easy-Medium | ~50 | Task Model |
| EDF Schedulability | Medium | ~60 | Task Model |
| EDF WCRT | Hard | ~80 | Task Model |
| Simulator | **Hard** | ~200 | Task Model, Policies |
| Test Generation | Easy | ~40 | Task Model |
| Experiments | Medium | ~100 | All above |
| Plotting | Easy-Medium | ~100 | matplotlib |
| Unit Tests | Easy | ~40 | All above |
| **Total** | | **~780** | |

**Recommended build order:** Task Model → CSV Loader → DM Analysis → Simulator (DM only) → Unit Tests → Cross-validate → EDF Analysis → Simulator (EDF) → Experiments → Plots.
