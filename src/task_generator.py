"""
Task Set Generator — UUniFast algorithm and random generation.

TODO: Implement task generation (currently stubbed).
"""

import random
from typing import List
from task_model import Task, TaskSet


def uunifast(n: int, U_total: float) -> List[float]:
    """
    UUniFast algorithm for generating n utilization values
    summing to U_total, uniformly distributed.
    """
    raise NotImplementedError("UUniFast not yet implemented")


def generate_task_set(
    n: int,
    U_total: float,
    period_range: tuple = (10, 100),
    deadline_factor_range: tuple = (0.5, 1.0)
) -> TaskSet:
    """Generate a random task set with n tasks and total utilization U_total."""
    raise NotImplementedError("Task generation not yet implemented")


def generate_implicit_deadline_set(n: int, U_total: float,
                                    period_range: tuple = (10, 100)) -> TaskSet:
    """Convenience: generate with D = T."""
    raise NotImplementedError("Task generation not yet implemented")
