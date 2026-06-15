"""
Plotting module — Visualization of scheduling analysis results.

TODO: Full implementation pending. Basic EDF plots available.
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List


def plot_edf_schedulability(results: Dict[float, dict],
                            title: str = "EDF Schedulability Ratio vs Utilization",
                            save_path: str = None):
    """Plot EDF schedulability ratio vs utilization from provided data."""
    utils = sorted(results.keys())
    edf_ratios = [results[u]['edf_ratio'] for u in utils]

    plt.figure(figsize=(10, 6))
    plt.plot(utils, edf_ratios, 'r-s', label='EDF', markersize=6, linewidth=2)
    plt.xlabel('Total Utilization')
    plt.ylabel('Schedulability Ratio')
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 1.05)
    plt.ylim(-0.05, 1.05)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_edf_wcrt_comparison(task_set, edf_wcrt, edf_sim, save_path: str = None):
    """Bar chart: EDF analytical WCRT vs simulated max response time per task."""
    task_ids = [t.id for t in task_set.tasks]
    x = np.arange(len(task_ids))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - width/2, [edf_wcrt[tid][0] for tid in task_ids], width,
           label='EDF Analytical WCRT', color='#e74c3c', alpha=0.8)
    ax.bar(x + width/2,
           [edf_sim[tid]['max_response_time'] if edf_sim[tid]['max_response_time'] else 0
            for tid in task_ids],
           width, label='EDF Simulated Max RT', color='#3498db', alpha=0.8)

    # Add deadline markers
    deadlines = [t.D for t in task_set.tasks]
    ax.scatter(x, deadlines, color='green', marker='v', s=100, zorder=5,
               label='Deadline')

    ax.set_xlabel('Task ID')
    ax.set_ylabel('Response Time')
    ax.set_title('EDF: Analytical WCRT vs Simulated Max Response Time')
    ax.set_xticks(x)
    ax.set_xticklabels([f'τ{tid}' for tid in task_ids])
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_schedulability_comparison(results: dict, title: str = "DM vs EDF Schedulability",
                                    save_path: str = None):
    """Plot DM vs EDF schedulability ratio vs utilization."""
    utils = sorted(results.keys())
    dm_ratios = [results[u]['dm_ratio'] for u in utils]
    edf_ratios = [results[u]['edf_ratio'] for u in utils]

    plt.figure(figsize=(10, 6))

    # Plot DM with thicker line and larger markers
    plt.plot(utils, dm_ratios, 'b-o', label='DM', markersize=10, linewidth=3, alpha=0.7)

    # Plot EDF with different marker style and thinner line on top
    plt.plot(utils, edf_ratios, 'r--s', label='EDF', markersize=8, linewidth=2, alpha=0.9)

    # Add text annotation if lines are identical
    if dm_ratios == edf_ratios:
        plt.text(0.5, 0.05, 'Note: DM and EDF have identical performance\n(lines overlap)',
                 transform=plt.gca().transAxes, fontsize=10, style='italic',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                 horizontalalignment='center')

    plt.xlabel('Total Utilization', fontsize=12)
    plt.ylabel('Schedulability Ratio', fontsize=12)
    plt.title(title, fontsize=14)
    plt.legend(loc='best', fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 1.05)
    plt.ylim(-0.05, 1.05)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_dm_schedulability(results: Dict[float, dict],
                           title: str = "DM Schedulability Ratio vs Utilization",
                           save_path: str = None):
    """Plot DM schedulability ratio vs utilization from provided data."""
    utils = sorted(results.keys())
    dm_ratios = [results[u]['dm_ratio'] for u in utils]

    plt.figure(figsize=(10, 6))
    plt.plot(utils, dm_ratios, 'b-o', label='DM', markersize=6, linewidth=2)
    plt.xlabel('Total Utilization')
    plt.ylabel('Schedulability Ratio')
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 1.05)
    plt.ylim(-0.05, 1.05)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_dm_wcrt_comparison(task_set, dm_wcrt, dm_sim, save_path: str = None):
    """Bar chart: DM analytical WCRT vs simulated max response time per task."""
    task_ids = [t.id for t in task_set.tasks]
    x = np.arange(len(task_ids))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - width/2, [dm_wcrt[tid][0] for tid in task_ids], width,
           label='DM Analytical WCRT', color='#e74c3c', alpha=0.8)
    ax.bar(x + width/2,
           [dm_sim[tid]['max_response_time'] if dm_sim[tid]['max_response_time'] else 0
            for tid in task_ids],
           width, label='DM Simulated Max RT', color='#3498db', alpha=0.8)

    # Add deadline markers
    deadlines = [t.D for t in task_set.tasks]
    ax.scatter(x, deadlines, color='green', marker='v', s=100, zorder=5,
               label='Deadline')

    ax.set_xlabel('Task ID')
    ax.set_ylabel('Response Time')
    ax.set_title('DM: Analytical WCRT vs Simulated Max Response Time')
    ax.set_xticks(x)
    ax.set_xticklabels([f'τ{tid}' for tid in task_ids])
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()


def plot_rt_distribution(rt_data: dict, save_path: str = None):
    """Histogram of observed response times. (Stub — needs full experiment data)"""
    raise NotImplementedError("Response time distribution plots not yet implemented")
