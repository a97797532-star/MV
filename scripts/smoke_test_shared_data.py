# 한글 안내: 합성 임시 데이터 또는 명시적으로 받은 실데이터로 공통 로더와 12개 입력 변환을 점검합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Portable CPU loader smoke test. Synthetic mode needs no private dataset or outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from mv_analysis.data import ManifestIndex, SingleViewDataset, FiveViewDataset, get_adapter, SPECS
from mv_analysis.data.collate import five_view_collate, detection_collate


# synthetic_index: 임시 폴더에 OK/NG 각1제품의 5시점 자료를 만들고 양성·빈·미제공 마스크 계약을 함께 구성합니다.
# 입력 인수: root.
def synthetic_index(root):
    manifest, annotations, boxes = [], [], []
    for status in ('OK', 'NG'):
        pid = f'synthetic/{status}/S0001'
        for view in ('C1', 'C2', 'C3', 'C4', 'C5'):
            relative = f'{pid}/{view}.jpg'
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            image = np.zeros((64, 64, 3), np.uint8)
            image[:] = [20, 60, 120]
            if not cv2.imwrite(str(path), image):
                raise RuntimeError('Synthetic JPEG write failed')
            stat = path.stat()
            manifest.append(dict(image_id=hashlib.sha256(relative.encode()).hexdigest()[:16],
                product_id=pid, category='synthetic', view=view, split='train',
                source_relative_path=relative, original_path=str(path),
                original_width=64, original_height=64,
                crop_x0=4, crop_y0=4, crop_x1=60, crop_y1=60,
                crop_width=56, crop_height=56, full_frame=False,
                coordinate_format='XYXY_EXCLUSIVE_ORIGINAL_PIXELS',
                policy_version='synthetic-smoke-v1', selected_policy='HUMAN_CROP',
                source_fingerprint=f'stat-v1:{stat.st_size}:{stat.st_mtime_ns}',
                additional_center_crop_allowed=False))
            has_mask = status == 'NG' and view != 'C2'
            mask_relative = relative[:-4] + '.png' if has_mask else ''
            annotations.append(dict(image_path=relative, product_id=pid, category='synthetic',
                view=view, split='train', status=status, has_mask=has_mask, mask_path=mask_relative))
            if has_mask:
                mask = np.zeros((64, 64), np.uint8)
                if view != 'C3':
                    mask[20:24, 30:34] = 255
                    boxes.append(dict(image_path=relative, class_id=0, x0=30, y0=20, x1=34, y1=24))
                if not cv2.imwrite(str(root / mask_relative), mask):
                    raise RuntimeError('Synthetic PNG write failed')
    classes = {'yolo': {'AK': 0}, 'coco': {'AK': 1}}
    return ManifestIndex(pd.DataFrame(manifest), pd.DataFrame(annotations), pd.DataFrame(boxes),
                         classes, data_root=root, require_complete=True)


# validate: 선택 제품의 모든 시점을 읽어 값 범위·타깃·배치·12개 입력 변환을 검증합니다. 실제 모델 forward는 하지 않습니다.
# 입력 인수: index, products.
def validate(index, products):
    # Preserve complete groups and include both labels when available.
    frame = index.data
    ordered = frame[['product_id', 'status']].drop_duplicates().sort_values(['status', 'product_id'])
    chosen = []
    for status in ('OK', 'NG'):
        ids = ordered.loc[ordered.status.eq(status), 'product_id'].tolist()
        if ids and len(chosen) < products:
            chosen.append(ids[0])
    chosen.extend(pid for pid in ordered.product_id if pid not in chosen)
    chosen = chosen[:products]
    ids = frame.loc[frame.product_id.isin(chosen), 'image_id']
    native = SingleViewDataset(index, image_ids=ids)
    states, contracts, image_count = {}, {}, 0
    for sample in native:
        image_count += 1
        image = sample['image']
        assert image.dtype == torch.float32 and image.shape[0] == 3
        assert torch.isfinite(image).all() and 0 <= image.min() <= image.max() <= 1
        if sample['mask'] is not None:
            assert sample['mask'].shape[-2:] == image.shape[-2:]
        if sample['status'] == 'NG' and sample['mask_status'] == 'MISSING':
            assert sample['mask'] is None and sample['detection_status'] == 'MISSING_ANNOTATION'
            assert not sample['detection_trainable']
        if sample['detection_trainable']:
            detection_collate([sample])
        states[sample['mask_status']] = states.get(sample['mask_status'], 0) + 1
        contracts[sample['detection_status']] = contracts.get(sample['detection_status'], 0) + 1
    adapted = SingleViewDataset(index, image_ids=ids, adapter=get_adapter('EfficientAD-S'))
    five = FiveViewDataset(adapted)
    batch = next(iter(DataLoader(five, batch_size=min(2, len(five)), num_workers=0,
                                collate_fn=five_view_collate)))
    assert batch['images'].shape[1:] == (5, 3, 256, 256)
    assert all(v == ['C1', 'C2', 'C3', 'C4', 'C5'] for v in batch['views'])
    adapter_shapes = {}
    for name in SPECS:
        sample = get_adapter(name)(native[0])
        assert sample['metadata']['adapter_spec']['model_integration'] == 'UNVERIFIED'
        adapter_shapes[name] = list(sample['image'].shape)
    return dict(status='PASSED', images=image_count, products=len(five),
        mask_states=states, detection_contracts=contracts,
        five_view_batch_shape=list(batch['images'].shape), adapters=adapter_shapes,
        manifest_sha256=index.sha256, model_forward=False, model_training=False)


# main: 명령행 인수를 읽고 본 파일의 처리 흐름을 실행합니다.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--bboxes', type=Path)
    parser.add_argument('--classes', type=Path)
    parser.add_argument('--data-root', type=Path, default=os.environ.get('REALIAD_DATA_ROOT'))
    parser.add_argument('--products', type=int, default=2)
    args = parser.parse_args()
    if args.products < 1:
        parser.error('--products must be positive')
    torch.set_num_threads(1)
    cv2.setNumThreads(1)
    if args.synthetic:
        if any((args.manifest, args.annotations, args.bboxes, args.classes)):
            parser.error('--synthetic cannot be combined with private annotation paths')
        with tempfile.TemporaryDirectory(prefix='mv-loader-smoke-') as folder:
            result = validate(synthetic_index(Path(folder)), args.products)
        result['mode'] = 'SYNTHETIC_TEMPORARY_DATA'
    else:
        required = ('manifest', 'annotations', 'bboxes', 'classes', 'data_root')
        for name in required:
            value = getattr(args, name)
            if value is None or not value.exists():
                parser.error(f'--{name.replace("_", "-")} must identify an existing private artifact; clone does not supply dataset files')
        index = ManifestIndex(args.manifest, args.annotations, args.bboxes, args.classes,
                              data_root=args.data_root, require_complete=True)
        result = validate(index, args.products)
        result['mode'] = 'REAL_DATA_READ_ONLY'
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
