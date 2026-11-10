# What changed in the agent's written reasoning?

The first standard run improved process-validation success from **13/256 (5.08%)** before training to **54/256 (21.09%)** at update 200. At the same time, its explicit reasoning text became shorter and increasingly identical to its answer.

| Measure, on the same 256 validation seeds | Before training | Update 200 |
| --- | --- | --- |
| Mean words in complete `<think>` spans | 25.07 | 3.79 |
| Think text equals answer, among complete pairs | 7/626 (1.12%) | 985/1009 (97.62%) |
| Complete thoughts mentioning box, target or wall | 641/725 (88.41%) | 0/1009 (0%) |

These denominators count model turns, not levels. One level can contain up to five turns, and malformed or incomplete tags are excluded from the corresponding text statistic. The model outputs the thought before the answer; "equals the answer" describes matching strings and does not imply it copied from a pre-existing answer key.

## Example: environment seed 123

Before training, its first response was:

```text
<think>You need to push all boxes to targets. Move to the left to start the process.</think> <answer>Left</answer>
```

This episode failed. At update 200, the first response on the same environment seed was:

```text
<think>Right || Down</think><answer>Right || Down</answer>
```

The later episode succeeded. This is an example of improved task success with less explicit state description; the first response alone is not the whole solution. Full board states, subsequent turns and episode outcomes are available in `results/case_studies.json` and the raw validation trajectories.

## Counterexample: environment seed 125

The initial first response incorrectly described two boxes on targets, although this task has one box. At update 200, the first response was:

```text
<think>Right || Down || Left</think><answer>Right || Down || Left</answer>
```

Both episodes failed. Short or duplicated thought text therefore does not imply success. The selected cases illustrate the aggregate pattern; they do not replace evaluation over all seeds.

## Repeated observation and limits

The two additional standard runs showed exact think/answer equality in every complete validation pair at update 200: **908/908** for training seed 43 and **911/911** for seed 44. Those are statistics on the 256 process-validation seeds. They should not be confused with the separate 512-seed held-out counts (1810/1811 and 1809/1809 respectively).

We analyzed only the text the model emitted. This cannot prove it stopped all internal reasoning, that every shorter explanation is worse, or that the full causal Echo Trap mechanism from the paper has been reproduced. The supported observation is narrower: task success increased while detailed written reasoning diminished in these standard-filter runs.

Recompute all measures with `python scripts/analyze.py --verify`; `results/validation_thinking.csv` contains every checkpoint of the first run, and `results/test_thinking_diagnostics.csv` covers all eight final models.
