#!/usr/bin/env bash
#SBATCH --job-name=cw-part1-coverage
#SBATCH --partition=4RTXq
#SBATCH --exclude=node[10-11]
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:nvidia_rtx_pro_6000_blackwell:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --array=0-14%3
set -euo pipefail
source "${CACHEWISE_STUDY_ROOT:?}/part1/environment.sh"
test -f "$TASK_ROOT/results/smoke/AUDITED_COMPLETE"
"$TASK_ROOT/.venv/bin/python" "$TASK_ROOT/part1/run.py" --root "$TASK_ROOT" --task-index "$SLURM_ARRAY_TASK_ID"
