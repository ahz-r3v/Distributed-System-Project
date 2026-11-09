#!/usr/bin/env bash
#SBATCH --job-name=cw-part1-validate
#SBATCH --partition=4RTXq
#SBATCH --exclude=node[10-11]
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:nvidia_rtx_pro_6000_blackwell:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=01:00:00
set -euo pipefail
source "${CACHEWISE_STUDY_ROOT:?}/part1/environment.sh"
cd "$TASK_ROOT/src/vllm-cachewise"
"$TASK_ROOT/.venv/bin/python" -m pytest --confcutdir=tests/v1/core/cachewise tests/v1/core/cachewise -q
cd "$TASK_ROOT"
"$TASK_ROOT/.venv/bin/python" -m pytest "$TASK_ROOT/part1/tests" -q
"$TASK_ROOT/.venv/bin/python" "$TASK_ROOT/part1/run.py" --root "$TASK_ROOT" --smoke
