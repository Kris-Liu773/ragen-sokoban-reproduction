# Reproduction guide

## Two ways to reproduce

1. **Audit the completed experiments on a CPU.** Clone this repository and run the analysis commands in the README. The raw evidence, figures and tables are included.
2. **Train new agents on a GPU.** Use the recorded configurations and the launcher below. Exact numeric agreement is not guaranteed: CUDA sampling and worker RNG state can vary, and the two historical continuations did not restore driver/environment RNG state.

The historical training and evaluation ran successfully on one NVIDIA H100 with 8 allocated CPU cores and 64 GB host memory. The original environment used Python 3.10 and inherited packages from an existing cluster environment. The new installation recipe below is reconstructed from its recorded versions, not a separately validated container image. The portable launcher's configuration and CPU analysis are tested; a fresh GPU installation of this packaging has not been tested. The first GPU command should therefore be the short smoke test.

## GPU installation

Use **Linux x86_64, Python 3.10**, and a driver compatible with the CUDA 12.4 PyTorch build. The FlashAttention wheel below is specifically for CPython 3.10, torch 2.6 and the pre-C++11 ABI. This training stack is not intended for macOS or CPU-only training.

```bash
python3.10 -m venv .venv-training
source .venv-training/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
  --index-url https://download.pytorch.org/whl/cu124
python -m pip install -r requirements-training.txt
python -m pip check
python -c 'import torch, vllm, flash_attn; print(torch.__version__, torch.version.cuda); print(torch.cuda.get_device_name(0))'
python scripts/download_model.py --out models/Qwen2.5-0.5B-Instruct
```

Run the CUDA device check inside a GPU allocation. Download the model where network access is permitted before launching an offline training job. `scripts/download_model.py` pins revision `7ae557604adf67be50417f59c2c2f167def9a775`; do not substitute the moving model-repository head if comparing with these runs.

The runtime source is already vendored. Do not install a current `verl` or `ragen` package over it. The launcher sets `PYTHONPATH` to the included source, disables online experiment tracking, and preserves the scheduler's `CUDA_VISIBLE_DEVICES`. The old upstream GSM8K data paths in the full config are unused by this environment-driven trainer; no GSM8K download is needed.

The core dependency pins are in `requirements-training.txt`. `provenance/observed-environment.txt` is a broader historical package inventory, **not an installation lock**: private editable-install paths and a local packaging wheel path were removed, and it contains packages unrelated to Sokoban.

## Inspect and smoke-test

```bash
# No model or GPU required for configuration generation; requires PyYAML.
python scripts/run.py train --run std_seed42 --model models/Qwen2.5-0.5B-Instruct \
  --out runs/config-check --dry-run

# GPU: three updates and 32 validation seeds, in a separate output directory.
python scripts/run.py smoke --run std_seed42 --model models/Qwen2.5-0.5B-Instruct \
  --out runs/smoke
```

Inspect `train.log`, `metrics.jsonl`, `validation_trajectories.jsonl`, and `exit_status.json`. A process exit code of zero does not imply 200 updates were reached: a soft runtime budget can stop a run early. Check the final `step` in `metrics.jsonl` and the checkpoint directory.

## Train the eight configurations

Valid run names are `std_seed42`, `std_seed43`, `std_seed44`, `random_seed42`, `random_seed43`, `random_seed44`, `penalty_seed42`, and `nofilter_seed42`.

```bash
python scripts/run.py train --run std_seed42 \
  --model models/Qwen2.5-0.5B-Instruct --out runs/std_seed42
```

Repeat with the other names and new output directories. By default the target is 200 updates with no soft time limit. `--train-seconds 5400` requests a soft budget for the training loop; initialization, validation and checkpoint writes add overhead, so this is not a strict wall-clock limit. The launcher refuses to overwrite any existing output directory.

Standard runs historically took about 51–52 minutes, while random/no-filter runs were slower. These timings depend strongly on generated response length and the amount of training data per update; they are not a guaranteed runtime. Preserve enough scheduler time for checkpointing and evaluation.

### Slurm

Activate the training environment and submit from the repository root:

```bash
sbatch -A YOUR_ACCOUNT -p YOUR_PARTITION slurm/train.sbatch std_seed42
```

The template requests one H100, 8 CPUs, 64 GB host memory and three hours, with a 2.5-hour soft training-loop budget. Adjust your site's GPU resource syntax, partition, time limit and budget. Run each experiment in a separate job or sequentially; do not run all eight concurrently on one GPU. This template contains no private cluster account or SSH configuration.

## Evaluate on the fixed held-out set

```bash
python scripts/run.py evaluate --run std_seed42 \
  --model models/Qwen2.5-0.5B-Instruct --out runs/test_std_seed42 \
  --checkpoint runs/std_seed42/checkpoints/global_step_200
```

Use the matching run name for each checkpoint. Evaluation uses 512 environment seeds beginning at 2,000,000, sampling temperature 0.5, and no added ineffective-action penalty. It does not update the model. The historical loader requires full actor and critic checkpoints, including model, optimizer and extra state; an exported Hugging Face actor-only model cannot be passed to this command.

Model checkpoints are not published in Git. These commands evaluate checkpoints you train locally. Existing experiment trajectories can be analyzed without downloading any weights.

## Resume an interrupted run

```bash
python scripts/run.py resume --run random_seed43 \
  --model models/Qwen2.5-0.5B-Instruct --out runs/random_seed43_continued \
  --checkpoint runs/random_seed43/checkpoints/global_step_191 --steps 200
```

Supply the actual checkpoint you have; routine saves occur every 20 updates, with additional saves at a budget stop and completion. Resume uses the matching recorded experiment settings and a new output directory. Model, optimizer, scheduler and worker RNG state are restored; the driver/environment RNG state is reinitialized. Treat a resumed run as a continuation with this limitation, not as a bitwise uninterrupted run or an additional independent seed.

## Data and analysis conventions

- `data/training/<run>/original/` contains the original logs. Two runs also have a `resumed/` directory.
- `data/evaluation/heldout_resumed_random_seed43/` and `heldout_resumed_nofilter_seed42/` supply the final update-200 results. Their earlier `heldout_random_seed43/` and `heldout_nofilter_seed42/` directories are preserved but are not counted in the final eight-model comparison.
- `.jsonl.gz` files decompress into the original bytes. Hashes, byte sizes and record counts are in `provenance/data_manifest.json`.
- Documentation is in English. Raw model outputs are preserved verbatim, including occasional multilingual or malformed output; translating them would change the evidence.
- For trajectory records, `step` is the model update, `seed` identifies the environment instance, `history` contains board states, model outputs, parsed actions and rewards, and `metrics` contains episode-level success.
- Missing action counters in the first training run are reported as unknown, not zero. A think/answer equality fraction with no complete pairs is also undefined, not zero.
- Matching text means exact equality after trimming leading/trailing whitespace inside complete `<think>` and `<answer>` tags. Word counts use whitespace splitting. Keyword matches use whole words `box/boxes`, `target/targets`, and `wall/walls`, ignoring case.
- The analysis of existing experiments uses an explicit eight-run manifest in `scripts/analyze.py`. New training outputs are kept under `runs/`; they do not silently replace the published evidence.

## Known limitations

There is one model size and one small environment. The three-seed comparison is exploratory; penalty and no-filter each have only one seed. No-filter uses 128 update episodes versus 32 for the other methods. Held-out seeds do not guarantee distinct puzzle layouts. Evaluation is sampled once per checkpoint, not averaged over repeated decoding seeds. The historical seed control varies driver/training environment randomness, while internal veRL/vLLM defaults remain unchanged. Written reasoning metrics cannot reveal hidden computation or prove the complete Echo Trap mechanism.
