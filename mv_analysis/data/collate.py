# 한글 안내: 크기가 다른 박스와 누락 마스크를 보존하며 배치를 구성하고 부적격 검출 타깃을 차단합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Preserve ragged boxes and None masks. No fake masks or implicit geometry."""
import torch

# single_view_collate: 이미지 크기가 같으면 Tensor로 쌓고, 다르면 목록으로 유지합니다. 박스와 None 마스크는 각 샘플 타깃에 남깁니다.
# 입력 인수: samples.
def single_view_collate(samples):
 images=[s['image'] for s in samples];same=len({tuple(i.shape) for i in images})==1
 return dict(images=torch.stack(images) if same else images,targets=[{k:v for k,v in s.items() if k!='image'} for s in samples],image_ids=[s['image_id'] for s in samples],product_ids=[s['product_id'] for s in samples])

# detection_collate: 검출용 이미지/타깃 목록을 만듭니다. strict 기본값은 미주석 NG나 무효 타깃이 빈 Negative로 들어가는 것을 차단합니다.
# 입력 인수: samples, strict.
def detection_collate(samples,strict=True):
 if strict and any(not s['detection_trainable'] for s in samples):raise ValueError('Non-supervised NG/invalid target cannot be passed as empty detection negative')
 return [s['image'] for s in samples],[{k:v for k,v in s.items() if k!='image'} for s in samples]

# five_view_collate: 5시점 제품 배치를 구성합니다. 시점 누락은 기본 오류이며 저장용 Padding은 명시한 경우에만 적용합니다.
# 입력 인수: samples, allow_partial, pad_storage.
def five_view_collate(samples,allow_partial=False,pad_storage=False):
 if not allow_partial and any(len(s['views'])!=5 or not s['metadata']['complete'] for s in samples):raise ValueError('Partial five-view samples are disabled')
 shapes={tuple(s['images'].shape) for s in samples}
 if len(shapes)!=1 and not allow_partial and not pad_storage:raise ValueError('Batch five-view shape mismatch; choose fixed-size adapter or explicit storage padding')
 tensors=[s['images'] for s in samples]
 if pad_storage:
  h=max(t.shape[-2] for t in tensors);w=max(t.shape[-1] for t in tensors);tensors=[torch.nn.functional.pad(t,(0,w-t.shape[-1],0,h-t.shape[-2])) for t in tensors];shapes={tuple(t.shape) for t in tensors}
 return dict(images=torch.stack(tensors) if len(shapes)==1 else tensors,product_ids=[s['product_id'] for s in samples],views=[s['views'] for s in samples],targets=[s['targets'] for s in samples],metadata=[s['metadata'] for s in samples])


# flatten_five_view_batch: 배치 저장용 Padding을 제거해 각 시점의 원래 입력 크기로 되돌립니다. 검출 학습 부적격 여부도 다시 검사합니다.
# 입력 인수: batch, strict_detection.
def flatten_five_view_batch(batch,*,strict_detection=True):
    """Remove explicit storage padding; restore per-view model tensors/targets exactly."""
    images=[];targets=[]
    for b,group in enumerate(batch['targets']):
        for v,target in enumerate(group):
            if strict_detection and target['metadata'].get('adapter_spec',{}).get('task')=='detection' and not target['detection_trainable']:
                raise ValueError('Invalid/unannotated per-view target cannot be flattened into detection training negatives')
            h,w=batch['metadata'][b]['valid_image_sizes'][v]
            images.append(batch['images'][b][v,:,:h,:w].contiguous())
            targets.append(target)
    return images,targets
