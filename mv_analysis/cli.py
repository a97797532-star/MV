from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
from .core import metadata,load_df,audit_masks,save_json
from . import stages
import cv2
cv2.setNumThreads(1)


def parser():
    p=argparse.ArgumentParser(description='Read-only Real-IAD analysis; new output for each execution')
    p.add_argument('--data-root',default=os.getenv('REALIAD_DATA_ROOT'))
    p.add_argument('--split-policy',choices=['hash','windows-project-v1'],default='hash')
    p.add_argument('--split-manifest',type=Path,default=os.getenv('REALIAD_SPLIT_MANIFEST'))
    p.add_argument('--output',type=Path,help='New run directory, or existing directory with --resume')
    p.add_argument('--resume',action='store_true',help='Explicitly continue an existing matching run')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ['validate-data','metadata','mask-audit','mask-thresholds','brightness','heatmap','bbox','resolution','report','run-all','regional-brightness']:
        s=sub.add_parser(name);s.add_argument('--limit',type=int);s.add_argument('--full',action='store_true');s.add_argument('--transfer-complete',action='store_true',help='Dataset owner confirms copying finished')
        s.add_argument('--inventory-only',action='store_true',help='Metadata without image decoding; cannot pass full preflight')
        s.add_argument('--heatmap-mode',choices=['presence','area'],default='presence')
        s.add_argument('--class-policy',choices=['defect_type','category_defect_type'],default='defect_type')
        if name=='regional-brightness':
            s.add_argument('--source-run',required=True,type=Path);s.add_argument('--sample',action='store_true');s.add_argument('--compare-methods',action='store_true');s.add_argument('--workers',type=int,default=1);s.add_argument('--batch-size',type=int,default=0);s.add_argument('--finalize',action='store_true');s.add_argument('--validation-evidence',type=Path)
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    if args.command=='regional-brightness':
        from .regional_cli import main as regional_main
        if args.limit is not None:raise SystemExit('Regional sample uses stratification: --sample, not --limit')
        target=args.output or Path('outputs')/datetime.now(timezone.utc).strftime('regional_%Y%m%dT%H%M%S%fZ')
        delegated=['--source-run',str(args.source_run),'--output',str(target),'--workers',str(args.workers),'--batch-size',str(args.batch_size)]
        for flag,value in [('--sample',args.sample),('--compare-methods',args.compare_methods),('--resume',args.resume),('--finalize',args.finalize)]:
            if value:delegated.append(flag)
        if args.validation_evidence:delegated.extend(['--validation-evidence',str(args.validation_evidence)])
        return regional_main(delegated)
    if args.limit is not None and args.limit<=0:raise SystemExit('--limit must be positive')
    if args.full and args.limit:raise SystemExit('--full and --limit cannot be combined')
    if args.command=='run-all' and not args.full and not args.limit:raise SystemExit('Specify --full or --limit N')
    if not args.data_root:raise SystemExit('Set REALIAD_DATA_ROOT or --data-root')
    root=Path(args.data_root).expanduser().resolve()
    if not root.is_dir():raise SystemExit(f'Dataset directory unavailable: {root}')
    out=(args.output or Path('outputs')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if out==root or root in out.parents or out in root.parents:raise SystemExit('Output and dataset must not contain each other')
    manifest=out/'run.json'
    if out.exists() and not args.resume:raise SystemExit('Output exists; choose a new directory or explicit --resume')
    out.mkdir(parents=True,exist_ok=True)
    lock=hashlib.sha256(Path('uv.lock').read_bytes()).hexdigest()
    source_hash=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path('mv_analysis').glob('*.py')))).hexdigest()
    config=dict(root=str(root),limit=args.limit,lock_sha256=lock,class_policy=args.class_policy,inventory_only=args.inventory_only,source_sha256=source_hash)
    if args.heatmap_mode!='presence':config['heatmap_mode']=args.heatmap_mode
    if args.split_policy!='hash':config['split_policy']=args.split_policy
    if args.split_manifest:
        config['split_manifest_sha256']=hashlib.sha256(Path(args.split_manifest).read_bytes()).hexdigest()
    if args.resume:
        if not manifest.exists():raise SystemExit('Resume manifest missing')
        previous=json.loads(manifest.read_text());old_config=previous['config']
        if {k:v for k,v in old_config.items() if k!='source_sha256'}!={k:v for k,v in config.items() if k!='source_sha256'}:raise SystemExit('Resume configuration mismatch')
        if old_config['source_sha256']!=source_hash:
            markers={'brightness':['brightness_per_image.jsonl'],'resolution':['resolution_checkpoint.jsonl'],'heatmap':['occupancy_known.npy'],'bbox':['yolo_labels','defect_bboxes.csv'],'mask-audit':['mask_policy.json'],'mask-thresholds':['mask_threshold_validation']}
            recorded=previous.get('stage_sources',{}).get(args.command)
            fresh=args.command in markers and not any((out/name).exists() for name in markers[args.command])
            if args.command!='report' and recorded!=source_hash and not fresh:raise SystemExit('Source changed for an existing stage; preserve results and start a new run')
        previous.setdefault('stage_sources',{})[args.command]=source_hash
        save_json(manifest,previous)
    else:save_json(manifest,dict(created=datetime.now(timezone.utc).isoformat(),config=config,commands=[],stage_sources={args.command:source_hash}))
    print(f'Output: {out}',flush=True)
    start=time.time();error=None
    try:
        if args.command in ('validate-data','metadata','run-all'):
            if not (args.resume and (out/'image_metadata_with_split.csv').exists()):
                df,validation=metadata(root,out,args.limit,not args.inventory_only,args.split_manifest,args.split_policy)
            else:df=load_df(out);validation=json.loads((out/'metadata_validation_report.json').read_text())
        elif args.command!='report':df=load_df(out)
        if args.command in ('validate-data','metadata') and validation['errors']:raise ValueError('Metadata has parse/decode errors; see validation report')
        if args.command=='mask-thresholds':
            from .mask_validation import validate_thresholds
            validate_thresholds(root,out,df)
        if args.command=='mask-audit':
            policy=audit_masks(root,df,out)
            if not policy['integrity_valid']:raise ValueError('Mask file integrity errors; see mask_policy.json')
        if args.command=='run-all':
            if args.full:
                if not args.transfer_complete:raise ValueError('Full analysis requires --transfer-complete after owner confirmation')
                if args.inventory_only or validation['errors'] or validation['orphan_masks']:
                    raise ValueError('Dataset validation failed')
                if shutil.disk_usage(out).free<10*1024**3:raise ValueError('Less than 10 GiB free disk space')
                preflight=Path('reports/preflight_passed.json')
                if not preflight.is_file():raise ValueError('Run scripts/record_preflight.py after a real smoke analysis')
                evidence=json.loads(preflight.read_text())
                if evidence.get('lock_sha256')!=lock or evidence.get('source_sha256')!=source_hash:raise ValueError('Preflight evidence stale; revalidate current source and lock')
            policy=audit_masks(root,df,out)
            stages.brightness(root,out,df,policy)
            stages.resolution(root,out,df)
            if policy['validated']:
                stages.heatmap(root,out,df,policy,args.heatmap_mode)
                stages.bbox(root,out,df,policy,args.class_policy)
            else:
                save_json(out/'mask_stages_deferred.json',dict(reason='Mask threshold requires review; independent image analysis continued',stages=['heatmap','bbox']))
            from .report import generate
            generate(out)
        elif args.command in ('brightness','heatmap','bbox','resolution'):
            policy=json.loads((out/'mask_policy.json').read_text()) if (out/'mask_policy.json').exists() else None
            if args.command in ('heatmap','bbox') and not (policy and policy['validated']):raise ValueError('Run mask-audit first; no validated mask policy')
            if args.command=='brightness':stages.brightness(root,out,df,policy)
            elif args.command=='heatmap':stages.heatmap(root,out,df,policy,args.heatmap_mode)
            elif args.command=='bbox':stages.bbox(root,out,df,policy,args.class_policy)
            else:stages.resolution(root,out,df)
        elif args.command=='report':
            from .report import generate
            generate(out)
    except Exception as exc:
        error=str(exc);print(error,file=sys.stderr)
    record=json.loads(manifest.read_text());record['commands'].append(dict(command=args.command,source_sha256=source_hash,argv=sys.argv[1:],elapsed_s=time.time()-start,error=error,finished=datetime.now(timezone.utc).isoformat()))
    save_json(manifest,record)
    return 1 if error else 0

if __name__=='__main__':raise SystemExit(main())
