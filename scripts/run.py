#!/usr/bin/env python3
"""Portable launcher using the recorded full configs; requires a Linux CUDA GPU."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'vendor/ragen'
RUNS = ['std_seed42','std_seed43','std_seed44','random_seed42','random_seed43',
        'random_seed44','penalty_seed42','nofilter_seed42']


def build_config(run, model, out, mode, checkpoint, steps):
    cfg = yaml.safe_load((ROOT/'configs/recorded'/f'{run}.yaml').read_text())
    def replace(v):
        if isinstance(v,dict):return {k:replace(x) for k,x in v.items()}
        if isinstance(v,list):return [replace(x) for x in v]
        if isinstance(v,str):
            return v.replace('__MODEL_PATH__',str(model)).replace('__OUTPUT_DIR__',str(out))
        return v
    cfg = replace(cfg)
    trainer = cfg['trainer']
    trainer.update(project_name='ragen-sokoban-reproduction', experiment_name=run+'-'+mode,
                   default_local_dir=str(out/'checkpoints'), default_hdfs_dir=None,
                   logger=['console'], n_gpus_per_node=1,
                   val_before_train=True, val_only=(mode=='evaluate'),
                   total_training_steps=steps, save_freq=20, test_freq=10,
                   resume_mode='resume_path' if checkpoint else 'disable',
                   resume_from_path=str(checkpoint) if checkpoint else None,
                   max_actor_ckpt_to_keep=2, max_critic_ckpt_to_keep=2)
    trainer['generations_to_log_to_wandb']['val']=0
    cfg['es_manager']['val']['seed_start']=2000000 if mode=='evaluate' else 123
    n=512 if mode=='evaluate' else 32 if mode=='smoke' else 256
    cfg['es_manager']['val']['env_groups']=n
    cfg['es_manager']['val']['env_configs']['n_groups']=[n]
    cfg['es_manager']['ineffective_action_penalty']=-0.1 if run=='penalty_seed42' and mode!='evaluate' else 0.0
    if mode=='smoke':
        trainer.update(total_training_steps=3, test_freq=3, save_freq=3)
    return cfg


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['train','smoke','resume','evaluate'])
    p.add_argument('--run',choices=RUNS,required=True)
    p.add_argument('--model',type=Path,required=True,help='Local directory of pinned model snapshot')
    p.add_argument('--out',type=Path,required=True,help='New output directory; never overwrites a run')
    p.add_argument('--checkpoint',type=Path,help='Full global_step_N directory with actor AND critic')
    p.add_argument('--steps',type=int,default=200)
    p.add_argument('--train-seconds',type=int,default=0,help='Soft training-loop budget; 0 disables it')
    p.add_argument('--dry-run',action='store_true',help='Validate and write config without loading GPU libraries')
    args=p.parse_args()
    args.model=args.model.expanduser().resolve()
    args.out=args.out.expanduser().resolve()
    if args.checkpoint:args.checkpoint=args.checkpoint.expanduser().resolve()
    if (args.mode in ['resume','evaluate']) != bool(args.checkpoint):
        p.error('resume/evaluate require --checkpoint; train/smoke require a fresh start')
    if args.steps<1 or args.train_seconds<0:p.error('steps must be positive and train-seconds nonnegative')
    if args.out.exists():p.error('Output directory exists; choose a new directory to preserve evidence')
    if not args.dry_run:
        if not (args.model/'config.json').is_file():p.error('Download the model first with scripts/download_model.py')
        if args.checkpoint:
            for role in ['actor','critic']:
                for prefix in ['model','optim','extra_state']:
                    if not (args.checkpoint/role/f'{prefix}_world_size_1_rank_0.pt').is_file():
                        p.error(f'Missing full checkpoint component: {role}/{prefix}')
    cfg=build_config(args.run,args.model,args.out,args.mode,args.checkpoint,args.steps)
    args.out.mkdir(parents=True)
    (args.out/'config.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
    seed=int(args.run.split('seed')[-1])
    command=[sys.executable,str(SOURCE/'train.py'),'--config-path',str(args.out),
             '--config-name','config','hydra.run.dir='+json.dumps(str(args.out/'hydra'))]
    metadata=dict(run=args.run,mode=args.mode,driver_seed=seed,command=command,
                  checkpoint=str(args.checkpoint) if args.checkpoint else None,
                  train_budget_seconds=args.train_seconds,dry_run=args.dry_run)
    (args.out/'run_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata,indent=2),flush=True)
    if args.dry_run:return
    env=os.environ.copy()
    env.update(PYTHONPATH=os.pathsep.join([str(SOURCE),str(SOURCE/'verl')]),
               PYTHONNOUSERSITE='1',RAGEN_SEED=str(seed),PYTHONHASHSEED=str(seed),
               RAGEN_OUTPUT_DIR=str(args.out),RAGEN_MAX_TRAIN_SECONDS=str(args.train_seconds),
               WANDB_MODE='offline',TOKENIZERS_PARALLELISM='false',
               OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',
               MPLBACKEND='Agg',PYTHONUNBUFFERED='1',HYDRA_FULL_ERROR='1',
               VLLM_USE_V1='0',VLLM_WORKER_MULTIPROC_METHOD='spawn',
               RAY_DEDUP_LOGS='1',RAY_USAGE_STATS_ENABLED='0',
               RAY_TMPDIR=f'/tmp/ragen-{os.getpid()}',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    # Preserve CUDA_VISIBLE_DEVICES supplied by the scheduler.
    with (args.out/'train.log').open('w') as log:
        process=subprocess.Popen(command,cwd=SOURCE,env=env,stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,text=True,bufsize=1)
        for line in process.stdout:
            print(line,end='',flush=True)
            log.write(line);log.flush()
        code=process.wait()
    (args.out/'exit_status.json').write_text(json.dumps({'exit_code':code})+'\n')
    raise SystemExit(code)


if __name__=='__main__':main()
