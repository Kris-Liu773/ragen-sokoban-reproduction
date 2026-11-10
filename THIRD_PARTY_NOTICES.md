# Third-party notices

This is an independent reproduction and extension. It is not an official RAGEN release.

| Component | Recorded upstream revision | License |
| --- | --- | --- |
| [RAGEN](https://github.com/RAGEN-AI/RAGEN) | `f92df5d67266af273d9c5ea4d25eb96d235b41ff` (first-paper code) | [MIT, Copyright 2025 RAGEN Team](vendor/ragen/LICENSE) |
| [veRL](https://github.com/volcengine/verl) | `797f9994b73f6335aa2349cdb2e9bb2a42f13f5c` | [Apache-2.0](vendor/ragen/verl/LICENSE); original per-file notices retained |
| [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) | `7ae557604adf67be50417f59c2c2f167def9a775` | Model is downloaded separately; refer to its model repository for terms |

New scripts, documentation and our modifications use the root MIT license. Vendored code remains subject to its existing license. We do not relicense veRL as MIT. Model weights, third-party wheels and external datasets are not bundled.

The vendored runtime was copied from the completed experiments. Our RAGEN changes are recorded in [the patch](provenance/ragen-experiment-changes.patch): local JSONL logging, fixed evaluation seed ranges, driver seeding, Slurm GPU visibility, random group selection, ineffective-action accounting and penalty, a soft runtime budget, and lazy optional API imports. The PPO configuration symlink is materialized as a regular file. One unrelated veRL comment was translated into English; executable code in that file is unchanged. [Source hashes](provenance/source_manifest.json) record both the experiment copy and the published copy.

Upstream examples, papers, images, notebooks and external WebShop dependencies were omitted. Only the Sokoban experiment is supported by this repository; some unused environment modules remain because the upstream registry imports them.

Please also cite the original [RAGEN paper](https://arxiv.org/abs/2504.20073) and acknowledge veRL when using their methods or implementation.
