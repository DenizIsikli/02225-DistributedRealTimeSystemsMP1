"""
Predefined test task sets for validation.
"""

from task_model import Task, TaskSet


def buttazzo_example() -> TaskSet:
    """Buttazzo Example (Section 4.5) — 3 tasks, all schedulable under DM & EDF."""
    return TaskSet([
        Task(id=1, T=10, C=3, D=7),
        Task(id=2, T=15, C=4, D=15),
        Task(id=3, T=20, C=2, D=20),
    ])


def harmonic_periods() -> TaskSet:
    """Simple harmonic periods — easy to verify by hand."""
    return TaskSet([
        Task(id=1, T=4,  C=1, D=4),
        Task(id=2, T=8,  C=2, D=8),
        Task(id=3, T=16, C=3, D=16),
    ])


def tight_utilization() -> TaskSet:
    """Tight utilization — DM fails, EDF succeeds."""
    return TaskSet([
        Task(id=1, T=6,  C=2, D=5),
        Task(id=2, T=8,  C=2, D=6),
        Task(id=3, T=12, C=3, D=12),
    ])


def single_task() -> TaskSet:
    """Trivial single-task set — WCRT must equal C."""
    return TaskSet([
        Task(id=1, T=10, C=3, D=10),
    ])


def high_utilization_edf() -> TaskSet:
    """
    High utilization (U ≈ 1.0) — EDF can schedule up to U=1,
    while DM fails earlier.
    """
    return TaskSet([
        Task(id=1, T=4, C=1, D=4),
        Task(id=2, T=6, C=2, D=6),
        Task(id=3, T=12, C=6, D=12),
    ])
