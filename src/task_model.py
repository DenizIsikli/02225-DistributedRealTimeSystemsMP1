"""
Task and TaskSet data structures for real-time scheduling analysis.
"""

from dataclasses import dataclass
from typing import List
import math
from functools import reduce

MAX_HYPERPERIOD = 100_000_000  # Safety cap to prevent OOM


def int_ceil_div(a: int, b: int) -> int:
    """Integer ceiling division: ⌈a/b⌉ without floating-point errors."""
    return (a + b - 1) // b


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
        assert self.C_best <= self.C, f"Task {self.id}: BCET={self.C_best} must be <= WCET={self.C}"
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
