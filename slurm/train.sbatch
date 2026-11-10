#!/usr/bin/env bash
#SBATCH --job-name=ragen-sokoban
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:h100:1
#SBATCH --time=03:00:00
#SBATCH --output=slurm-%j.out

# Submit from the repository root after activating the training environment.
# Supply your allocation and partition with sbatch -A ... -p ... .
# Usage: sbatch -A YOUR_ACCOUNT -p YOUR_PARTITION slurm/train.sbatch std_seed42
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit from the repository root}"
run="${1:-std_seed42}"
python scripts/run.py train --run "$run" \
  --model "${RAGEN_MODEL_DIR:-$PWD/models/Qwen2.5-0.5B-Instruct}" \
  --out "$PWD/runs/${run}-${SLURM_JOB_ID}" \
  --train-seconds 9000
