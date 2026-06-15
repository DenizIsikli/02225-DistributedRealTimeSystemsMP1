"""
Comparator — Runs experiments, collects results for DM vs EDF comparison.
"""

from pathlib import Path
from typing import Dict, List
from csv_loader import load_all_util_levels
from edf_analysis import edf_schedulability_test, compute_edf_wcrt
from dm_analysis import is_dm_schedulable, compute_dm_wcrt
from simulator import Simulator, EDFPolicy, DMPolicy
from task_model import TaskSet


def experiment_edf_schedulability_from_data(base_path: Path) -> Dict[float, dict]:
    """
    For each utilization level in the provided data, compute the fraction
    of task sets schedulable under EDF.

    Returns dict: util -> {'edf_ratio': float, 'count': int}
    """
    data = load_all_util_levels(base_path)
    results = {}

    for util, sets in sorted(data.items()):
        edf_count = sum(1 for ts in sets if edf_schedulability_test(ts))
        results[util] = {
            'edf_ratio': edf_count / len(sets) if sets else 0.0,
            'count': len(sets)
        }

    return results


def experiment_edf_wcrt_vs_simulation(task_set: TaskSet):
    """
    Compare EDF analytical WCRT with simulated max response times.
    Runs simulation with WCET to get worst-case observed response.
    """
    edf_wcrt = compute_edf_wcrt(task_set)
    edf_sim = Simulator(task_set, EDFPolicy(), use_wcet=True).run()

    print(f"\n{'Task':<8} {'EDF WCRT':<12} {'EDF Sim':<12} {'Match':<8}")
    print("-" * 42)
    for task in task_set.tasks:
        tid = task.id
        analytical = edf_wcrt[tid][0]
        simulated = edf_sim[tid]['max_response_time']
        match = "✓" if analytical == simulated else "✗"
        print(f"τ{tid:<7} {analytical:<12} {simulated:<12} {match:<8}")

    return edf_wcrt, edf_sim


def experiment_dm_schedulability_from_data(base_path: Path) -> Dict[float, dict]:
    """
    For each utilization level in the provided data, compute the fraction
    of task sets schedulable under DM.

    Returns dict: util -> {'dm_ratio': float, 'count': int}
    """
    data = load_all_util_levels(base_path)
    results = {}

    for util, sets in sorted(data.items()):
        dm_count = sum(1 for ts in sets if is_dm_schedulable(ts))
        results[util] = {
            'dm_ratio': dm_count / len(sets) if sets else 0.0,
            'count': len(sets)
        }

    return results


def experiment_dm_wcrt_vs_simulation(task_set: TaskSet):
    """
    Compare DM analytical WCRT with simulated max response times.
    Runs simulation with WCET to get worst-case observed response.
    """
    # Compute DM WCRT (this also assigns priorities)
    dm_wcrt = compute_dm_wcrt(task_set)

    # Create priority mapping for DMPolicy
    task_priorities = {task.id: task.priority for task in task_set.tasks}

    # Run simulation with DM policy
    dm_sim = Simulator(task_set, DMPolicy(task_priorities), use_wcet=True).run()

    print(f"\n{'Task':<8} {'DM WCRT':<12} {'DM Sim':<12} {'Match':<8}")
    print("-" * 42)
    for task in task_set.tasks:
        tid = task.id
        analytical = dm_wcrt[tid][0]
        simulated = dm_sim[tid]['max_response_time']
        match = "✓" if analytical == simulated else "✗"
        print(f"τ{tid:<7} {analytical:<12} {simulated:<12} {match:<8}")

    return dm_wcrt, dm_sim


def experiment_dm_vs_edf_comparison(base_path: Path) -> Dict[float, dict]:
    """
    Compare DM vs EDF schedulability ratios across utilization levels.

    Returns dict: util -> {'dm_ratio': float, 'edf_ratio': float, 'count': int}
    """
    data = load_all_util_levels(base_path)
    results = {}

    for util, sets in sorted(data.items()):
        dm_count = sum(1 for ts in sets if is_dm_schedulable(ts))
        edf_count = sum(1 for ts in sets if edf_schedulability_test(ts))

        results[util] = {
            'dm_ratio': dm_count / len(sets) if sets else 0.0,
            'edf_ratio': edf_count / len(sets) if sets else 0.0,
            'count': len(sets)
        }

    return results


