#!/usr/bin/env bash
set -e

ROOT_OUT="../output"
TASKS=25
SETS=20
CORES=1
JITTER=0

UTILS=(10 20 30 40 50 60 70 80 90 100)


for U in "${UTILS[@]}"; do
  UTIL_FMT=$(printf "0.%02d-util" "$U")
  if [ "$U" -eq 100 ]; then
    UTIL_FMT="1.00-util"
  fi

  # -------------------------
  # UUniFast
  # -------------------------
  OUTDIR="${ROOT_OUT}/unifast-utilDist/uniform-discrete-perDist/${CORES}-core/${TASKS}-task/${JITTER}-jitter/${UTIL_FMT}"
  mkdir -p "$OUTDIR"

  rm -f taskset-*.csv
  python task_generator.py -n "$TASKS" -s "$SETS" -u "$U" -g 1 -m 0 -p "$CORES"

  i=0
  for f in taskset-*.csv; do
    mv "$f" "${OUTDIR}/taskset_${i}.csv"
    i=$((i+1))
  done

  # -------------------------
  # Automotive
  # -------------------------
  OUTDIR="${ROOT_OUT}/automotive-utilDist/automotive-perDist/${CORES}-core/${TASKS}-task/${JITTER}-jitter/${UTIL_FMT}"
  mkdir -p "$OUTDIR"

  rm -f taskset-*.csv
  python task_generator.py -n "$TASKS" -s "$SETS" -u "$U" -g 0 -m 0 -p "$CORES"

  i=0
  for f in taskset-*.csv; do
    mv "$f" "${OUTDIR}/taskset_${i}.csv"
    i=$((i+1))
  done
done

echo "Done."