# Real-Time Scheduling Analysis: DM vs EDF

This project implements schedulability analysis and worst-case response time (WCRT) computation for periodic real-time task sets using **Deadline Monotonic (DM)** and **Earliest Deadline First (EDF)** scheduling algorithms.

## Setup and Installation

### 1. Download Task Set Data

Download the task set data from:
**[DTU Learn - Mini Project 1 Data](https://learn.inside.dtu.dk/d2l/le/lessons/296251/topics/1151672)**

After downloading, **extract and copy the `output` folder to the root directory** of this project:

```text
mini-project-1-RTDS/
├── output/              ← Place the downloaded data here
│   ├── automotive-utilDist/
│   └── uunifast-utilDist/
├── src/
├── results/
└── README.md
```

### 2. Install Dependencies

Install required Python packages:

```powershell
pip install -r requirements.txt
```

Required packages:
- `numpy` - Numerical computations
- `matplotlib` - Plotting results
- `pandas` - CSV data loading

---

## Running the Analysis

### Run All Experiments

```powershell
python src/main.py
```

### Run Specific Algorithms

**EDF Analysis Only:**

```powershell
python src/main.py --algorithm edf
```

**DM Analysis Only:**

```powershell
python src/main.py --algorithm dm
```

**Compare DM vs EDF:**

```powershell
python src/main.py --compare
```

### Run on Specific Datasets

**Automotive Dataset (D = T):**

```powershell
python src/main.py --data automotive
```

**UUniFast Dataset (D < T):**

```powershell
python src/main.py --data uunifast
```

### Run Validation Tests

```powershell
python src/main.py --test
```

---

## Results

All generated plots are saved in the **`results/`** folder:

- `edf_schedulability_automotive.png` - EDF schedulability ratio vs utilization (automotive dataset)
- `edf_schedulability_uunifast.png` - EDF schedulability ratio vs utilization (UUniFast dataset)
- `dm_schedulability_automotive.png` - DM schedulability ratio vs utilization (automotive dataset)
- `dm_schedulability_uunifast.png` - DM schedulability ratio vs utilization (UUniFast dataset)
- `dm_vs_edf_automotive.png` - Comparison of DM and EDF schedulability (automotive)
- `dm_vs_edf_uunifast.png` - Comparison of DM and EDF schedulability (UUniFast)

---

## Algorithm Descriptions

### Earliest Deadline First (EDF)

**EDF** is a **dynamic priority** scheduling algorithm that assigns priorities based on absolute deadlines at runtime. The job with the earliest absolute deadline has the highest priority.

**Key Properties:**
- **Optimal** for single-processor systems with preemption
- Dynamic priority assignment
- Works for both constrained (D ≤ T) and arbitrary deadline systems

**Schedulability Test:**
This implementation uses the **Processor Demand Approach**:
- Task set is schedulable if: `h(L) ≤ L` for all relevant time points `L`
- `h(L)` = processor demand = total execution time demanded by all jobs with both release and deadline within `[0, L]`

**WCRT Computation:**
- Computes the synchronous busy period `W` (when all tasks release at time 0)
- For each task, finds the worst-case response time by checking demand at critical time points
- Critical points are tested within the busy period to find maximum response time

**Formula:**

```text
h(L) = Σ (⌊(L - D_i) / T_i⌋ + 1) · C_i   for all tasks with D_i ≤ L
```

### Deadline Monotonic (DM)

**DM** is a **fixed priority** scheduling algorithm that assigns static priorities based on relative deadlines. Tasks with shorter deadlines receive higher priorities.

**Key Properties:**
- Fixed priority assignment (priority never changes)
- Optimal among fixed-priority algorithms for constrained deadlines (D ≤ T)
- Similar to Rate Monotonic (RM), but uses deadlines instead of periods

**Priority Assignment:**
- Tasks sorted by deadline (ascending)
- Shorter deadline → Higher priority (lower priority number)

**Schedulability Test & WCRT:**
Uses **Response Time Analysis (RTA)** with fixed-point iteration:

```text
R_i^(0) = C_i
R_i^(n+1) = C_i + Σ_{j ∈ hp(i)} ⌈R_i^(n) / T_j⌉ · C_j
```

Where:
- `R_i` = worst-case response time of task `τ_i`
- `C_i` = worst-case execution time
- `hp(i)` = set of higher-priority tasks
- `T_j` = period of higher-priority task `τ_j`

The iteration continues until convergence or until `R_i > D_i` (unschedulable).

**Schedulable if:** `R_i ≤ D_i` for all tasks

---

## Project Structure

### Core Files

- **`main.py`** - Main entry point; orchestrates all experiments and analysis
- **`task_model.py`** - Defines `Task` and `TaskSet` data classes for task representation
- **`edf_analysis.py`** - EDF schedulability test and WCRT computation (Processor Demand Approach)
- **`dm_analysis.py`** - DM priority assignment, schedulability test, and WCRT computation (Response Time Analysis)
- **`simulator.py`** - Discrete-event simulator for EDF and DM scheduling policies
- **`comparator.py`** - Runs experiments comparing analytical results with simulation
- **`csv_loader.py`** - Loads task sets from CSV files in the `output/` directory
- **`plotter.py`** - Generates plots and saves results to `results/` folder
- **`test_cases.py`** - Provides known test cases for validation (Buttazzo examples, harmonic periods, etc.)

### Test Files

- **`tests/test_edf.py`** - Unit tests for EDF analysis
- **`tests/test_dm.py`** - Unit tests for DM analysis
- **`tests/test_simulator.py`** - Unit tests for the simulator

### Data Directories

- **`output/`** - Contains task set CSV files (must be downloaded and placed here)
  - `automotive-utilDist/` - Task sets with D = T (deadline equals period)
  - `uunifast-utilDist/` - Task sets with D < T (constrained deadlines)
- **`results/`** - Generated plots and analysis results

---

## Dataset Information

### Automotive Dataset (D = T)

- Deadlines equal to periods (`D_i = T_i`)
- Periods follow automotive application patterns
- 25 tasks per task set
- Utilization levels from 10% to 100%

### UUniFast Dataset (D < T)

- Constrained deadlines (`D_i < T_i`)
- Periods uniformly distributed
- Task utilization generated using UUniFast algorithm
- 25 tasks per task set
- Utilization levels from 10% to 100%

---

## References

This project is based on course **02225 Distributed Real-Time Systems** at DTU.

**Key References:**
- Buttazzo, G. C. (2011). *Hard Real-Time Computing Systems: Predictable Scheduling Algorithms and Applications*
  - Section 4.5: Deadline Monotonic
  - Section 4.6: EDF with Deadlines Less Than Periods
- Lehoczky, J. (1990). *Rate Monotonic vs. EDF: Judgment Day*

---

## Task Model

Each task `τ_i` is characterized by:
- **`C`** - Worst-Case Execution Time (WCET)
- **`T`** - Period (minimum inter-arrival time)
- **`D`** - Relative Deadline
- **`id`** - Unique task identifier
- **`priority`** - Priority level (assigned by DM)

Constraints:
- `C ≤ D ≤ T`
- All tasks are periodic and independent
- Single processor, preemptive scheduling

---

## Author

Created as part of the Mini-Project 1 for **02225 Distributed Real-Time Systems** course at DTU.
