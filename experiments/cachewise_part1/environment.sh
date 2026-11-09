#!/usr/bin/env bash
# Source from a Slurm allocation; never run the model on the login server.
set -euo pipefail
TASK_ROOT="${CACHEWISE_STUDY_ROOT:?Set the frozen study root}"
TASK_SCRATCH="/local/cachewise-part1-$USER-${SLURM_JOB_ID:?Requires a GPU job}"
mkdir -p "$TASK_SCRATCH/tmp" "$TASK_SCRATCH/vllm" "$TASK_SCRATCH/triton" "$TASK_SCRATCH/lib"
export TMPDIR="$TASK_SCRATCH/tmp"
export VLLM_CACHE_ROOT="$TASK_SCRATCH/vllm"
export TRITON_CACHE_DIR="$TASK_SCRATCH/triton"
export CUDA_HOME="$TASK_ROOT/.venv/lib/python3.12/site-packages/nvidia/cu13"
export PATH="$TASK_ROOT/.venv/bin:$CUDA_HOME/bin:$PATH"
ln -s "$CUDA_HOME/lib/libcudart.so.13" "$TASK_SCRATCH/lib/libcudart.so"
export FLASHINFER_EXTRA_LDFLAGS="-L$TASK_SCRATCH/lib -L$CUDA_HOME/lib"
export OMP_NUM_THREADS=8
export HF_HUB_OFFLINE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$TASK_ROOT/src/vllm-cachewise:$TASK_ROOT/serving_experiment${PYTHONPATH:+:$PYTHONPATH}"
cd "$TASK_ROOT"
