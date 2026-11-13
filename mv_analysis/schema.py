# 한글 안내: Real-IAD 분석 파이프라인의 공통 기능입니다. 입력 자료와 설정의 기존 계약을 유지합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Standard-library-only dataset layout inspection."""
import hashlib
import os
import re
from pathlib import Path
VIEWS={f"C{i}" for i in range(1,6)}

# parse_image: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: path, root.
def parse_image(path, root):
    rel = path.relative_to(root)
    parts = rel.parts
    if len(parts) < 4 or parts[1] not in ('OK', 'NG'):
        raise ValueError(f'Unsupported layout: {rel}')
    match = re.fullmatch(r'(.+)_([0-9]+)_(OK|NG)_(?:(.+)_)?(C[1-5])_([0-9]+)', path.stem)
    if not match:
        raise ValueError(f'Unsupported filename: {rel}')
    category, number, status, defect, view, stamp = match.groups()
    filename_category=category
    category=category.rstrip('_')
    if category != parts[0] or status != parts[1]:
        raise ValueError(f'Filename/layout disagreement: {rel}')
    defect = defect or 'OK'
    if status=='NG' and len(parts)<5:raise ValueError(f'Incomplete NG layout: {rel}')
    directory_defect=parts[2] if status=='NG' else 'OK'
    filename_defect=defect
    label_conflict=directory_defect!=filename_defect
    if label_conflict:defect='UNRESOLVED'
    # Conservatively keep identical category+serial together across OK/NG/time.
    # Physical identity cannot be established from serial reuse alone.
    product_id = f'{category}/{number}'
    capture_id = f'{category}/{status}/{defect}/{number}/{stamp}'
    bucket = int(hashlib.sha256(product_id.encode()).hexdigest()[:8], 16) % 100
    split = 'train' if bucket < 70 else 'validation' if bucket < 85 else 'test'
    has_mask=path.with_suffix('.png').is_file()
    return dict(label_conflict=label_conflict,filename_defect_type=filename_defect,directory_defect_type=directory_defect,filename_category_token=filename_category,has_mask=has_mask,image_path=str(rel), category=category, status=status, defect_type=defect,
                view=view, product_id=product_id, capture_id=capture_id, split=split,
                mask_path=str(rel.with_suffix('.png')) if has_mask else '')


# scan: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: root.
def scan(root):
    images, masks, others = [], [], 0
    for base, _, files in os.walk(root):
        for filename in files:
            p = Path(base) / filename
            if p.suffix.lower() in ('.jpg', '.jpeg'):
                images.append(p)
            elif p.suffix.lower() == '.png':
                masks.append(p)
            else:
                others += 1
    return sorted(images), sorted(masks), others

