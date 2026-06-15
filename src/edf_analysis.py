"""
EDF Scheduling Analysis — Processor Demand Approach + WCRT Computation.

Fully implemented module for Earliest Deadline First schedulability testing
and worst-case response time computation for constrained-deadline task sets.
"""

from task_model import Task, TaskSet, int_ceil_div
from typing import List, Dict, Tuple


def compute_synchronous_busy_period(task_set: TaskSet) -> int:
    """
    Compute the synchronous busy period W using fixed-point iteration:
        W^(0) = Σ C_i
        W^(n+1) = Σ ⌈W^(n) / T_i⌉ · C_i
    This is the level-0 busy period length when all tasks release at time 0.
    Used as the upper bound for EDF WCRT computation.
    """
    tasks = task_set.tasks
    W = sum(t.C for t in tasks)
    max_W = task_set.hyperperiod
    max_iter = 10_000

    for _ in range(max_iter):
        W_new = sum(int_ceil_div(W, t.T) * t.C for t in tasks)
        if W_new == W:
            return W
        if W_new > max_W:
            return max_W
        W = W_new

    return W


def compute_demand(tasks: List[Task], L: int) -> int:
    """
    Processor demand h(L): total execution time demanded in [0, L]
    by all jobs with both release and deadline within [0, L].

    h(L) = Σ_{i: D_i ≤ L} (⌊(L - D_i) / T_i⌋ + 1) · C_i
    """
    demand = 0
    for t in tasks:
        if t.D <= L:
            num_jobs = (L - t.D) // t.T + 1
            demand += num_jobs * t.C
    return demand


def compute_L_star(task_set: TaskSet) -> int:
    """
    Compute the upper bound L* for the processor demand testing interval.
    Uses iterative fixed-point computation on the synchronous busy period.

    Returns -1 if U >= 1 (unschedulable — busy period diverges).
    """
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
    """
    Generate all absolute deadline points d_{i,k} = D_i + k*T_i
    up to L* for the processor demand test.
    """
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
    Processor Demand Approach (Buttazzo Section 4.6.1).

    For constrained deadlines (D_i ≤ T_i), schedulable iff:
        ∀L ∈ D: h(L) ≤ L
    where D is the set of absolute deadlines up to L*.
    """
    U = task_set.utilization
    if U > 1.0:
        return False

    # For implicit deadlines (D_i == T_i for all), U <= 1 is sufficient
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


def compute_edf_wcrt(task_set: TaskSet) -> Dict[int, Tuple[int, bool]]:
    """
    Compute WCRT for each task under EDF scheduling.

    For each task τ_i, examines all job instances within the busy period
    and finds the maximum response time. Under synchronous release (worst case),
    computes finish time for each job iteratively.

    Returns:
        dict mapping task_id -> (wcrt, schedulable)
    """
    tasks = task_set.tasks
    results = {}

    # Use synchronous busy period as upper bound (not L_star from demand test,
    # which can be 0 for implicit-deadline low-utilization sets)
    busy_period = compute_synchronous_busy_period(task_set)

    for task_i in tasks:
        max_response = 0

        k = 0
        while True:
            release_time = k * task_i.T
            if release_time >= busy_period:
                break

            finish_time = _compute_edf_job_finish(tasks, task_i, k, busy_period)
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

    Uses iterative fixed-point computation. The workload function accounts
    for all jobs (from all tasks) whose absolute deadline is ≤ the target
    job's absolute deadline, and that have been released by time t.
    """
    release = job_index * target.T
    abs_deadline = release + target.D

    def workload(t):
        """Total work from jobs with deadline ≤ abs_deadline, released by time t."""
        w = 0
        for task in tasks:
            if task.id == target.id:
                # Count jobs of the target task up to and including job_index
                jobs = min(job_index + 1, t // task.T + 1 if t >= 0 else 0)
                w += jobs * task.C
            else:
                # Only include jobs whose absolute deadline ≤ target's
                if abs_deadline < task.D:
                    continue
                # Max k such that D_j + k*T_j ≤ abs_deadline
                max_k_deadline = (abs_deadline - task.D) // task.T
                # Max k such that k*T_j ≤ t (i.e., released by time t)
                max_k_released = t // task.T if t >= 0 else -1
                jobs = min(max_k_deadline, max_k_released) + 1
                if jobs > 0:
                    w += jobs * task.C
        return w

    # Initial estimate
    t = workload(0)
    for _ in range(10_000):
        t_new = workload(t)
        if t_new == t:
            return t
        if t_new > L_star * 2:
            return t_new  # Diverging — unschedulable
        t = t_new

    return t
