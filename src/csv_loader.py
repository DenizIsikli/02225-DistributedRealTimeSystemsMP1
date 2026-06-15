"""
CSV Loader — Parse provided CSV task sets from the output/ directory.
"""

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

def load_taskset_simple(csv_path: Path) -> TaskSet:
    """
    Load CSV files with header:
    Task,BCET,WCET,Period,Deadline,Priority
    Supports Task IDs like 'Task_0'.
    """
    tasks = []

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            task_id_str = row['Task']
            # Handle formats like "Task_0"
            task_id = int(task_id_str.replace("Task_", ""))

            tasks.append(Task(
                id=task_id,
                T=int(row['Period']),
                C=int(row['WCET']),
                D=int(row['Deadline']),
                C_best=max(1, int(row['BCET']))
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
