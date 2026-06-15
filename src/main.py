"""
Main entry point — orchestrates EDF and DM analysis, simulation, and comparison.

Usage:
    python main.py                     # Run all experiments
    python main.py --test              # Run validation test cases
    python main.py --data automotive   # Run on automotive dataset
    python main.py --data uunifast     # Run on UUniFast dataset
    python main.py --algorithm dm      # Run DM analysis only
    python main.py --algorithm edf     # Run EDF analysis only
    python main.py --compare           # Run DM vs EDF comparison
"""

import argparse
import sys
from pathlib import Path

from task_model import TaskSet
from edf_analysis import edf_schedulability_test, compute_edf_wcrt
from dm_analysis import is_dm_schedulable, compute_dm_wcrt
from simulator import Simulator, EDFPolicy, DMPolicy
from csv_loader import load_taskset, load_all_util_levels
from test_cases import buttazzo_example, harmonic_periods, tight_utilization, single_task
from comparator import (experiment_edf_schedulability_from_data, experiment_edf_wcrt_vs_simulation,
                       experiment_dm_schedulability_from_data, experiment_dm_wcrt_vs_simulation,
                       experiment_dm_vs_edf_comparison)


# Paths to provided data
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTOMOTIVE_PATH = PROJECT_ROOT / "output" / "automotive-utilDist" / "automotive-perDist" / "1-core" / "25-task" / "0-jitter"
UUNIFAST_PATH = PROJECT_ROOT / "output" / "uunifast-utilDist" / "uniform-discrete-perDist" / "1-core" / "25-task" / "0-jitter"
RESULTS_DIR = PROJECT_ROOT / "results"


def run_validation_tests():
    """Run EDF and DM analysis on known test cases and validate with simulation."""
    print("=" * 60)
    print("VALIDATION: EDF and DM Analysis on Known Test Cases")
    print("=" * 60)

    test_sets = {
        "Buttazzo Example": buttazzo_example(),
        "Harmonic Periods": harmonic_periods(),
        "Tight Utilization": tight_utilization(),
        "Single Task": single_task(),
    }

    for name, ts in test_sets.items():
        print(f"\n--- {name} ---")
        print(f"Tasks: {ts.tasks}")
        print(f"Utilization: {ts.utilization:.4f}")
        print(f"Implicit deadlines: {ts.all_implicit_deadlines()}")

        # EDF schedulability test
        edf_sched = edf_schedulability_test(ts)
        print(f"EDF Schedulable: {edf_sched}")

        # DM schedulability test
        dm_sched = is_dm_schedulable(ts)
        print(f"DM Schedulable: {dm_sched}")

        # EDF WCRT
        if edf_sched:
            edf_wcrt = compute_edf_wcrt(ts)
            print(f"EDF WCRTs: ", end="")
            for tid, (wcrt, sched) in sorted(edf_wcrt.items()):
                print(f"τ{tid}: R={wcrt} ({'OK' if sched else 'MISS'})", end="  ")
            print()

        # DM WCRT
        if dm_sched:
            dm_wcrt = compute_dm_wcrt(ts)
            print(f"DM WCRTs: ", end="")
            for tid, (wcrt, sched) in sorted(dm_wcrt.items()):
                print(f"τ{tid}: R={wcrt} ({'OK' if sched else 'MISS'})", end="  ")
            print()

        # Simulation cross-validation
        if edf_sched:
            print("\nEDF Cross-validation (Analytical vs Simulation):")
            experiment_edf_wcrt_vs_simulation(ts)

        if dm_sched:
            print("\nDM Cross-validation (Analytical vs Simulation):")
            experiment_dm_wcrt_vs_simulation(ts)


def run_edf_on_dataset(dataset_name: str):
    """Run EDF schedulability analysis on provided dataset."""
    if dataset_name == "automotive":
        base_path = AUTOMOTIVE_PATH
    elif dataset_name == "uunifast":
        base_path = UUNIFAST_PATH
    else:
        print(f"Unknown dataset: {dataset_name}")
        return

    if not base_path.exists():
        print(f"Dataset path not found: {base_path}")
        return

    print("=" * 60)
    print(f"EDF Schedulability Analysis — {dataset_name} dataset")
    print("=" * 60)

    results = experiment_edf_schedulability_from_data(base_path)

    print(f"\n{'Util':<10} {'EDF Ratio':<15} {'Count':<10}")
    print("-" * 35)
    for util, data in sorted(results.items()):
        print(f"{util:<10.2f} {data['edf_ratio']:<15.4f} {data['count']:<10}")

    # Try to plot (non-fatal if display unavailable)
    try:
        RESULTS_DIR.mkdir(exist_ok=True)
        from plotter import plot_edf_schedulability
        save_path = str(RESULTS_DIR / f"edf_schedulability_{dataset_name}.png")
        plot_edf_schedulability(results,
                                title=f"EDF Schedulability — {dataset_name}",
                                save_path=save_path)
        print(f"\nPlot saved to {save_path}")
    except Exception as e:
        print(f"\nPlotting skipped: {e}")


def run_edf_wcrt_example():
    """Run EDF WCRT on a sample CSV task set and compare with simulation."""
    # Pick a sample file
    sample_csv = AUTOMOTIVE_PATH / "0.50-util" / "tasksets" / "automotive_0.csv"
    if not sample_csv.exists():
        print(f"Sample CSV not found: {sample_csv}")
        return

    print("=" * 60)
    print(f"EDF WCRT Analysis — Sample: {sample_csv.name}")
    print("=" * 60)

    ts = load_taskset(sample_csv)
    print(f"Tasks: {ts.size()}, Utilization: {ts.utilization:.4f}")

    edf_sched = edf_schedulability_test(ts)
    print(f"EDF Schedulable: {edf_sched}")

    if edf_sched:
        experiment_edf_wcrt_vs_simulation(ts)


def run_dm_on_dataset(dataset_name: str):
    """Run DM schedulability analysis on provided dataset."""
    if dataset_name == "automotive":
        base_path = AUTOMOTIVE_PATH
    elif dataset_name == "uunifast":
        base_path = UUNIFAST_PATH
    else:
        print(f"Unknown dataset: {dataset_name}")
        return

    if not base_path.exists():
        print(f"Dataset path not found: {base_path}")
        return

    print("=" * 60)
    print(f"DM Schedulability Analysis — {dataset_name} dataset")
    print("=" * 60)

    results = experiment_dm_schedulability_from_data(base_path)

    print(f"\n{'Util':<10} {'DM Ratio':<15} {'Count':<10}")
    print("-" * 35)
    for util, data in sorted(results.items()):
        print(f"{util:<10.2f} {data['dm_ratio']:<15.4f} {data['count']:<10}")

    # Try to plot (non-fatal if display unavailable)
    try:
        RESULTS_DIR.mkdir(exist_ok=True)
        from plotter import plot_dm_schedulability
        save_path = str(RESULTS_DIR / f"dm_schedulability_{dataset_name}.png")
        plot_dm_schedulability(results,
                              title=f"DM Schedulability — {dataset_name}",
                              save_path=save_path)
        print(f"\nPlot saved to {save_path}")
    except Exception as e:
        print(f"\nPlotting skipped: {e}")


def run_dm_vs_edf_comparison(dataset_name: str):
    """Run DM vs EDF comparison on provided dataset."""
    if dataset_name == "automotive":
        base_path = AUTOMOTIVE_PATH
    elif dataset_name == "uunifast":
        base_path = UUNIFAST_PATH
    else:
        print(f"Unknown dataset: {dataset_name}")
        return

    if not base_path.exists():
        print(f"Dataset path not found: {base_path}")
        return

    print("=" * 60)
    print(f"DM vs EDF Comparison — {dataset_name} dataset")
    print("=" * 60)

    results = experiment_dm_vs_edf_comparison(base_path)

    print(f"\n{'Util':<10} {'DM Ratio':<15} {'EDF Ratio':<15} {'Count':<10}")
    print("-" * 50)
    for util, data in sorted(results.items()):
        print(f"{util:<10.2f} {data['dm_ratio']:<15.4f} {data['edf_ratio']:<15.4f} {data['count']:<10}")

    # Try to plot (non-fatal if display unavailable)
    try:
        RESULTS_DIR.mkdir(exist_ok=True)
        from plotter import plot_schedulability_comparison
        save_path = str(RESULTS_DIR / f"dm_vs_edf_{dataset_name}.png")
        plot_schedulability_comparison(results,
                                      title=f"DM vs EDF Schedulability — {dataset_name}",
                                      save_path=save_path)
        print(f"\nPlot saved to {save_path}")
    except Exception as e:
        print(f"\nPlotting skipped: {e}")

def run_csv_folder(folder: str):
    from pathlib import Path
    from csv_loader import load_taskset_simple
    from edf_analysis import edf_schedulability_test, compute_edf_wcrt
    from dm_analysis import is_dm_schedulable, compute_dm_wcrt

    folder_path = Path(folder)
    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    output_file = results_dir / f"csv_results_{folder_path.name}.txt"

    with open(output_file, "w") as out:
        for file in sorted(folder_path.rglob("*.csv")):
            ts = load_taskset_simple(file)

            out.write("=" * 60 + "\n")
            out.write(f"CSV TEST: {file.name}\n")
            out.write("=" * 60 + "\n")

            out.write(f"Utilization: {ts.utilization:.4f}\n")

            edf_sched = edf_schedulability_test(ts)
            dm_sched = is_dm_schedulable(ts)

            out.write(f"EDF Schedulable: {edf_sched}\n")
            out.write(f"DM Schedulable: {dm_sched}\n")

            if edf_sched:
                edf_wcrt = compute_edf_wcrt(ts)
                out.write("EDF WCRTs: " +
                          str({tid: wcrt for tid, (wcrt, _) in edf_wcrt.items()}) + "\n")

            if dm_sched:
                dm_wcrt = compute_dm_wcrt(ts)
                out.write("DM WCRTs: " +
                          str({tid: wcrt for tid, (wcrt, _) in dm_wcrt.items()}) + "\n")

            out.write("\n")

    print(f"Results saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="DRTS Mini-Project 1 — EDF and DM Analysis")
    parser.add_argument('--test', action='store_true', help='Run validation test cases')
    parser.add_argument('--data', choices=['automotive', 'uunifast'],
                        help='Run analysis on provided dataset')
    parser.add_argument('--algorithm', choices=['edf', 'dm', 'both'],
                        help='Choose scheduling algorithm to analyze')
    parser.add_argument('--compare', action='store_true',
                        help='Run DM vs EDF comparison')
    parser.add_argument('--sample', action='store_true',
                        help='Run WCRT on a sample CSV task set')
    parser.add_argument('--all', action='store_true',
                        help='Run all available experiments')
    parser.add_argument('--csv', help='Run CSV task sets from folder')

    args = parser.parse_args()

    # Default: run everything if no flags specified
    if not any([args.test, args.data, args.sample, args.all, args.compare, args.algorithm]):
        args.all = True

    # Default algorithm is both if not specified
    if args.data and not args.algorithm:
        args.algorithm = 'both'

    if args.csv:
        run_csv_folder(args.csv)
        return

    if args.test or args.all:
        run_validation_tests()

    if args.compare or args.all:
        if args.data:
            run_dm_vs_edf_comparison(args.data)
        else:
            print("\n")
            run_dm_vs_edf_comparison("automotive")
            print("\n")
            run_dm_vs_edf_comparison("uunifast")
    elif args.data:
        # Run analysis based on algorithm choice
        if args.algorithm in ['edf', 'both']:
            run_edf_on_dataset(args.data)
        if args.algorithm in ['dm', 'both']:
            print("\n")
            run_dm_on_dataset(args.data)
    elif args.all:
        # Run both algorithms on both datasets
        run_edf_on_dataset("automotive")
        print("\n")
        run_dm_on_dataset("automotive")
        print("\n")
        run_edf_on_dataset("uunifast")
        print("\n")
        run_dm_on_dataset("uunifast")

    if args.sample or args.all:
        print("\n")
        run_edf_wcrt_example()


if __name__ == "__main__":
    main()
