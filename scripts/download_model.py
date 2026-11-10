#!/usr/bin/env python3
"""Download the exact base-model revision used in these experiments."""
import argparse
from huggingface_hub import snapshot_download

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', default='models/Qwen2.5-0.5B-Instruct')
args = p.parse_args()
print(snapshot_download(repo_id='Qwen/Qwen2.5-0.5B-Instruct',
    revision='7ae557604adf67be50417f59c2c2f167def9a775', local_dir=args.out))
