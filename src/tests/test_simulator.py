"""
Unit tests for the discrete-event simulator (EDF policy).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_cases import buttazzo_example, harmonic_periods, single_task
from edf_analysis import compute_edf_wcrt
from simulator import Simulator, EDFPolicy
from task_model import Task, TaskSet


def test_simulator_edf_single_task():
    """Single task: simulated max RT should equal WCET."""
    ts = single_task()
    sim = Simulator(ts, EDFPolicy(), use_wcet=True)
    results = sim.run()
    assert results[1]['max_response_time'] == 3, \
        f"Expected max RT = 3, got {results[1]['max_response_time']}"
    assert results[1]['deadline_misses'] == 0


def test_simulator_edf_buttazzo():
    """Simulator EDF max RTs should match analytical WCRTs for Buttazzo example."""
    ts = buttazzo_example()
    analytical = compute_edf_wcrt(ts)
    sim = Simulator(ts, EDFPolicy(), use_wcet=True)
    sim_results = sim.run()

    for task in ts.tasks:
        tid = task.id
        sim_rt = sim_results[tid]['max_response_time']
        ana_rt = analytical[tid][0]
        # Simulated should be ≤ analytical (simulator sees one hyperperiod,
        # analytical considers all possible busy periods)
        assert sim_rt <= ana_rt, \
            f"Task {tid}: simulated RT {sim_rt} > analytical WCRT {ana_rt}"
        assert sim_results[tid]['deadline_misses'] == 0, \
            f"Task {tid}: unexpected deadline miss"


def test_simulator_edf_harmonic():
    """Harmonic periods: no deadline misses under EDF."""
    ts = harmonic_periods()
    sim = Simulator(ts, EDFPolicy(), use_wcet=True)
    results = sim.run()
    for task in ts.tasks:
        assert results[task.id]['deadline_misses'] == 0, \
            f"Task {task.id}: unexpected deadline miss"


def test_simulator_edf_no_jobs_lost():
    """All released jobs within simulation should complete."""
    ts = buttazzo_example()
    sim = Simulator(ts, EDFPolicy(), use_wcet=True)
    results = sim.run()
    # Over one hyperperiod, each task should have hyperperiod/T jobs
    hp = ts.hyperperiod
    for task in ts.tasks:
        expected_jobs = hp // task.T
        actual_jobs = results[task.id]['num_jobs']
        assert actual_jobs == expected_jobs, \
            f"Task {task.id}: expected {expected_jobs} jobs, got {actual_jobs}"


def run_all_tests():
    """Run all simulator tests and report results."""
    tests = [
        test_simulator_edf_single_task,
        test_simulator_edf_buttazzo,
        test_simulator_edf_harmonic,
        test_simulator_edf_no_jobs_lost,
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
    print("Running Simulator (EDF) unit tests...\n")
    success = run_all_tests()
    sys.exit(0 if success else 1)
