"""
Deadline Monotonic (DM) Scheduling Analysis.

Priority assignment and WCRT computation under fixed-priority DM scheduling.
DM assigns priorities based on relative deadlines: shorter deadline = higher priority.
"""

from task_model import Task, TaskSet, int_ceil_div
from typing import Dict, Tuple, List


def assign_dm_priorities(task_set: TaskSet) -> None:
    """
    Assign DM priorities: shorter deadline = higher priority (lower number).

    Priority 1 is highest, priority n is lowest.
    Modifies the task_set in place by setting the priority field of each task.
    """
    # Sort tasks by deadline (ascending)
    sorted_tasks = sorted(task_set.tasks, key=lambda t: (t.D, t.id))

    # Assign priorities (1 = highest priority)
    for priority, task in enumerate(sorted_tasks, start=1):
        task.priority = priority


def compute_dm_wcrt(task_set: TaskSet) -> Dict[int, Tuple[int, bool]]:
    """
    Compute WCRT for each task under DM scheduling using the
    Response Time Analysis (RTA) approach.

    For each task τ_i, the WCRT R_i is computed using fixed-point iteration:
        R_i^(0) = C_i
        R_i^(n+1) = C_i + Σ_{j∈hp(i)} ⌈R_i^(n) / T_j⌉ · C_j

    where hp(i) is the set of tasks with higher priority than τ_i.

    Returns:
        dict mapping task_id -> (wcrt, schedulable)
    """
    # Ensure priorities are assigned
    assign_dm_priorities(task_set)

    results = {}

    for task in task_set.tasks:
        wcrt = _compute_task_wcrt(task, task_set.tasks)
        schedulable = wcrt <= task.D
        results[task.id] = (wcrt, schedulable)

    return results


def _compute_task_wcrt(task: Task, all_tasks: List[Task]) -> int:
    """
    Compute WCRT for a single task using fixed-point iteration.

    R_i = C_i + interference from higher-priority tasks
    """
    # Get higher-priority tasks
    hp_tasks = [t for t in all_tasks if t.priority < task.priority]

    # Initial response time
    R = task.C
    max_iterations = 1000

    # Early termination bound: if R exceeds this, task is unschedulable
    # Use deadline as reasonable upper bound, or period if deadline is larger
    max_response = max(task.D, task.T) * 2

    # Fixed-point iteration
    for iteration in range(max_iterations):
        # Interference from higher-priority tasks
        interference = sum(
            int_ceil_div(R, hp_task.T) * hp_task.C
            for hp_task in hp_tasks
        )

        R_new = task.C + interference

        # Convergence check
        if R_new == R:
            return R

        # Divergence check - response time exceeds reasonable bound
        if R_new > max_response:
            return R_new  # Return large value indicating unschedulability

        # Oscillation detection - if R isn't decreasing and exceeds deadline
        if R_new > task.D and iteration > 10:
            if R_new >= R:  # Not converging
                return R_new

        R = R_new

    # Max iterations reached - likely unschedulable
    return R


def is_dm_schedulable(task_set: TaskSet) -> bool:
    """
    Check if the entire task set is schedulable under DM.

    A task set is schedulable if all tasks meet their deadlines,
    i.e., R_i ≤ D_i for all tasks τ_i.
    """
    wcrt_results = compute_dm_wcrt(task_set)
    return all(schedulable for _, schedulable in wcrt_results.values())


def dm_utilization_bound(n: int) -> float:
    """
    Compute the Liu & Layland utilization bound for n tasks under RM/DM.

    U_bound(n) = n * (2^(1/n) - 1)

    This is a sufficient (but not necessary) schedulability condition.
    For large n, this approaches ln(2) ≈ 0.693.
    """
    if n <= 0:
        return 0.0
    return n * (2.0 ** (1.0 / n) - 1.0)


def dm_schedulability_test_sufficient(task_set: TaskSet) -> bool:
    """
    Quick sufficient schedulability test using Liu & Layland bound.

    If U ≤ n(2^(1/n) - 1), the task set is guaranteed schedulable.
    However, this test is not necessary — a task set may still be
    schedulable even if it fails this test.

    Returns:
        True if definitely schedulable, False if unknown (requires WCRT analysis)
    """
    n = len(task_set.tasks)
    bound = dm_utilization_bound(n)
    return task_set.utilization <= bound


def dm_hyperbolic_bound_test(task_set: TaskSet) -> bool:
    """
    Hyperbolic bound test for DM schedulability (Bini et al., 2003).

    A task set is schedulable if:
        ∏_{i=1}^{n} (U_i + 1) ≤ 2

    This is less pessimistic than Liu & Layland bound.

    Returns:
        True if definitely schedulable, False if unknown
    """
    product = 1.0
    for task in task_set.tasks:
        utilization = task.C / task.T
        product *= (utilization + 1.0)

    return product <= 2.0
