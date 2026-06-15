"""
Unit tests for EDF analysis module.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_cases import buttazzo_example, harmonic_periods, tight_utilization, single_task, high_utilization_edf
from edf_analysis import edf_schedulability_test, compute_edf_wcrt, compute_demand, compute_L_star
from task_model import Task, TaskSet


def test_edf_schedulability_buttazzo():
    """Buttazzo example should be schedulable under EDF."""
    ts = buttazzo_example()
    assert edf_schedulability_test(ts) == True, "Buttazzo example should be EDF-schedulable"


def test_edf_schedulability_harmonic():
    """Harmonic periods should be schedulable under EDF."""
    ts = harmonic_periods()
    assert edf_schedulability_test(ts) == True, "Harmonic example should be EDF-schedulable"


def test_edf_schedulability_tight():
    """Tight utilization should be schedulable under EDF (even if DM fails)."""
    ts = tight_utilization()
    assert edf_schedulability_test(ts) == True, "Tight utilization should be EDF-schedulable"


def test_edf_schedulability_single():
    """Single task should always be schedulable."""
    ts = single_task()
    assert edf_schedulability_test(ts) == True


def test_edf_unschedulable_overload():
    """Overloaded task set (U > 1) should be unschedulable."""
    ts = TaskSet([
        Task(id=1, T=4, C=3, D=4),
        Task(id=2, T=6, C=3, D=6),
    ])
    # U = 3/4 + 3/6 = 0.75 + 0.5 = 1.25 > 1
    assert edf_schedulability_test(ts) == False, "Overloaded set should be unschedulable"


def test_edf_wcrt_single_task():
    """Single task WCRT should equal its WCET."""
    ts = single_task()
    results = compute_edf_wcrt(ts)
    assert results[1][0] == 3, f"Single task WCRT should be 3, got {results[1][0]}"
    assert results[1][1] == True, "Single task should be schedulable"


def test_edf_wcrt_buttazzo():
    """Check EDF WCRTs for Buttazzo example."""
    ts = buttazzo_example()
    results = compute_edf_wcrt(ts)
    # All tasks should be schedulable
    for tid, (wcrt, sched) in results.items():
        assert sched == True, f"Task {tid} should be EDF-schedulable"
        task = next(t for t in ts.tasks if t.id == tid)
        assert wcrt <= task.D, f"Task {tid}: WCRT {wcrt} exceeds deadline {task.D}"


def test_edf_wcrt_harmonic():
    """Check EDF WCRTs for harmonic example."""
    ts = harmonic_periods()
    results = compute_edf_wcrt(ts)
    for tid, (wcrt, sched) in results.items():
        assert sched == True, f"Task {tid} should be EDF-schedulable"


def test_demand_function():
    """Test processor demand computation on simple case."""
    ts = buttazzo_example()
    # At L = D_1 = 7, only task 1 contributes: 1 job × C_1 = 3
    d = compute_demand(ts.tasks, 7)
    assert d == 3, f"Demand at L=7 should be 3 (only τ1), got {d}"

    # At L = 10, tasks 1 and 3 contribute (D_1=7 ≤ 10, D_3=20 > 10, D_2=15 > 10)
    # Wait: D_1=7 ≤ 10 → floor((10-7)/10)+1 = 1 job → 3
    d = compute_demand(ts.tasks, 10)
    assert d == 3, f"Demand at L=10 should be 3, got {d}"


def test_implicit_deadline_shortcut():
    """For implicit deadlines, EDF only needs U ≤ 1."""
    ts = TaskSet([
        Task(id=1, T=10, C=5, D=10),
        Task(id=2, T=20, C=5, D=20),
    ])
    # U = 0.5 + 0.25 = 0.75 ≤ 1
    assert ts.all_implicit_deadlines() == True
    assert edf_schedulability_test(ts) == True


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        test_edf_schedulability_buttazzo,
        test_edf_schedulability_harmonic,
        test_edf_schedulability_tight,
        test_edf_schedulability_single,
        test_edf_unschedulable_overload,
        test_edf_wcrt_single_task,
        test_edf_wcrt_buttazzo,
        test_edf_wcrt_harmonic,
        test_demand_function,
        test_implicit_deadline_shortcut,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__} — {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__} — {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed")
    return failed == 0


if __name__ == "__main__":
    print("Running EDF unit tests...\n")
    success = run_all_tests()
    sys.exit(0 if success else 1)
