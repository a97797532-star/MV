# 한글 안내: 파일명에 해당하는 분석·검증·보고 작업의 실행 스크립트입니다. 인수와 출력 위치를 확인한 뒤 실행합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Document statically inspected pinned source; never instantiate or train a model."""
import json,hashlib,re
from pathlib import Path
B=Path('outputs/model_sources_20261112_v1')
OUT=Path('reports/MODEL_INPUT_REQUIREMENTS.md')
IM='mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]'
records=[]
# add: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: name, key, size, geometry, color, normal, dtype, box, mask, train, aug, constraint, refs, unknown.
def add(name,key,size,geometry,color,normal,dtype,box,mask,train,aug,constraint,refs,unknown):
 records.append(dict(model=name,repo_key=key,input_resolution=size,resize_crop=geometry,color_channels=color,
 normalization=normal,dtype_range_tensor=dtype,bbox=box,mask=mask,training=train,augmentation=aug,
 resolution_constraints=constraint,references=refs,unverified=unknown,source_status='VERIFIED',runtime_status='UNVERIFIED'))
add('PatchCore','patchcore','CLI resize256 / imagesize224',
 'MVTecDataset: Resize(256)短辺保持→CenterCrop224。1024正方形では原本896相当が残る。','RGB/3; PIL convert RGB',IM,
 'ToTensor: uint8→CHW浮動小数/0..1、その後Normalize。通常float32だが実行dtypeはUNVERIFIED。','対象外（異常スコア・画素マップ）。',
 '評価時Resize→同じCenterCrop→ToTensor。マスクResizeの補間は明示されず選択依存の確認が必要。正常評価のゼロマスクと未提供NGは分離する。',
 '正常Trainの特徴をmemory bankに保存する方式。NGは評価用。Real-IAD adapterは未実装・未実行。','選択MVTecDatasetには幾何/色のランダム増強なし。',
 '出力画像サイズを変更可能だが特徴抽出・memory bank・校正を再構成する必要。',
 [('src/patchcore/datasets/mvtec.py','class MVTecDataset'),('bin/run_patchcore.py','--resize')],
 'FAISS/encoder実行、選ぶ重み、依存torchvision版と補間/antialias、画像サイズ変更時の性能。')
add('EfficientAD-S','efficientad','image_size=256, model_size=small',
 'default_transform: Resize((256,256)); 解析対象画像にはCenterCropなし。ImageNet penalty側はResize512→RandomGrayscale→CenterCrop256で別経路。',
 'ImageFolder PILのRGB/3を期待。Real-IAD adapter未検証。',IM,
 'ToTensor後CHW/0..1→Normalize。通常float32; 実行未確認。','対象外。',
 '選択スクリプトの評価はGT tif/pngを参照する。評価マスクの補間/座標をReal-IAD用に別途確認。',
 '正常画像のteacher/student/AE学習。NGを正常学習へ混ぜない。外部ImageNet penaltyは別入力でdefault path noneなら無効。',
 'AE分岐でbrightness/contrast/saturation各0.2のColorJitterをRandomChoice。',
 'teacher/AE空間出力を合わせる構造。任意解像度はUNVERIFIED。共通CenterCropを勝手に追加しない。',
 [('efficientad.py','image_size = 256'),('efficientad.py','default_transform'),('common.py','class ImageFolderWithoutTarget')],
 'anomalib版との入力正規化/teacher内部処理の差、checkpoint、mask adapter、解像度変更対応。')
for name,key in [('UniAD','uniad'),('HVQ-Trans','hvqtrans')]:
 add(name,key,'MVTec config input_size=[224,224]',
  'BaseTransformTrain/Test: 正方形Resize224。CenterCropなし。',
  'image_reader color_mode RGB/3 (OpenCV readerがRGBへ変換)。',IM,
  'PIL画像→ToTensor/0..1→Normalize、mask ToTensor。通常float32; runtime未検証。',
  '対象外（再構成異常検知）。',
  'image BILINEAR, mask NEARESTをbase_datasetで明記。custom_datasetは未提供NG maskを全領域255にする経路があるためそのまま流用禁止。',
  '選択trainメタファイルは正常学習を前提。メタファイルの個別labelまでは未取得でUNVERIFIED。Real-IADでは正常Trainのみ別manifestにする。',
  '選択config train hflip/vflip/rotate=False; 独自transformクラスが存在しても有効とは扱わない。',
  'input_sizeに依存する特徴grid/position embedding/decoder設定との整合が必要。任意変更動作UNVERIFIED。',
  [('experiments/MVTec-AD/config.yaml','input_size'),('datasets/base_dataset.py','class TrainBaseTransform'),('datasets/custom_dataset.py','np.ones'),('datasets/image_reader.py','RGB')],
  'Python3.12互換性、選択train.json内容、任意解像度、実行dtypeと各checkpointは未検証。')
for name,key,entry in [('Dinomaly','dinomaly','dinomaly_realiad_sep.py'),('INP-Former','inpformer','INP_Former_Single_Class.py')]:
 add(name,key,'Resize448→CenterCrop392（選択単一クラス経路）',
  'get_data_transforms: Resize((448,448))→ToTensor→CenterCrop392→Normalize。正方形原本では896相当を保持。',
  'dataset PIL convert RGB/3。',IM,
  'CHW浮動小数; Normalize前0..1。通常float32だが実行設定はUNVERIFIED。','対象外。',
  'GTもResize→CenterCrop→ToTensorだが補間指定なし。マスクの軟化・境界shiftを検証し、独自NEAREST adapterとの違いを明記する。',
  '正常Trainによる再構成系異常検知。NGは評価。単一/多クラスなど別entryでは設定が異なり得る。',
  '標準get_data_transformsはランダム増強なし。get_strong_transformsも定義されるが選択entryでの使用有無を区別。',
  'DINO系patch14、392=28×14。任意サイズ時のpositional interpolationやtoken整合は実行前検証。追加の共通Cropとの二重Cropに注意。',
  [('dataset.py','def get_data_transforms'),(entry,'crop_size'),(entry,'448')],
  'encoder重みと実行時token制約、強増強の実際の有効設定、mask補間の版差、モデル性能はUNVERIFIED。')
for name,path in [('Faster R-CNN','faster_rcnn'),('RetinaNet','retinanet')]:
 add(name,'torchvision','constructor min_size800 / max_size1333',
  'GeneralizedRCNNTransform: 短辺800・長辺上限1333、aspect保持、batch pad(size_divisible=32)。CenterCropなし。weight factoryがkwargsを変更する場合は別検証。',
  'RGB/3、list[CHW Tensor]。',IM+' をmodel内部で適用。外部で二重Normalizeしない。',
  '入力float [0,1]。通常float32。モデル変換前のuint8は不可、AMP/FP16はUNVERIFIED。',
  '絶対座標XYXY [x0,y0,x1,y1], float; positive area。labels int64で0背景、欠陥クラス1..8。正常画像はshape(0,4) boxes/empty labels。',
  'このBBox detectorにpixel mask入力は不要。未提供NGを負例にしない。',
  'OKはobjectなしnegative、位置ラベル付きNGはpositive。mask未提供NGはobject教師から除外/別弱教師として検討。',
  'constructor自身はランダム画像増強なし。references/detection presetは学習recipeごとにflip等が異なる。選ぶweights/recipeはUNVERIFIED。',
  'min/max_sizeで変更可能だが外部Resize512の後に内部800への再拡大を避ける設定設計が必要。anchor/検出headの小物体評価を行う。',
  [(f'torchvision/models/detection/{path}.py','min_size=800'),('torchvision/models/detection/transform.py','def normalize'),('torchvision/models/detection/transform.py','mode="bilinear"')],
  '選ぶbackbone/weights presetと正確なtrain augmentation、AMP/FP16、Real-IAD adapterの実行。')
add('YOLO11','yolo11','shared Ultralytics config imgsz640',
 'LetterBox、aspect保持、padding。CenterCropなし。INTER_LINEARがLetterBoxの明示default。Trainのmosaic等は別幾何経路。',
 'loader BGR→Formatで通常RGB/3 (bgr probability default0)。',
 'detectorの前処理は/255、通常ImageNet mean/stdは適用しない。',
 'FormatでCHW tensor、train preprocess_batchでfloat()/255、predict half指定経路あり。FP32/0..1を基準、実行FP16未検証。',
 'YOLO labelは0開始class + normalized cx cy w h。原本XYXYを最終adapterで変換しletterbox offsetを記録。',
 'BBox taskではmask不要。segmentation taskのmask変換とは分ける。',
 '正常画像empty labels、位置ラベル付きNG positive。未提供NGを空ラベル負例にしない。',
 'このcommitの共有default: hsv_h .015/s .7/v .4, translate .1, scale .5, fliplr .5, mosaic1, mixup0, cutmix0。YOLO11固有の確定recipeではなく選択するoverrideを未確定とする。',
 'stride倍数・letterbox挙動・rect設定をadapterで確認。取得commitは現行ライブラリで、YOLO11 architecture variant/checkpointは未選定。',
 [('ultralytics/cfg/default.yaml','imgsz:'),('ultralytics/data/augment.py','class LetterBox'),('ultralytics/data/augment.py','class Format'),('ultralytics/models/yolo/detect/train.py','preprocess_batch')],
 'YOLO11 n/s/m/l/xの最終variant、固定library release、weightsごとの入力/recipe overrideはUNVERIFIED。')
add('RT-DETRv2','rtdetrv2','rtdetrv2 include dataloader 640×640',
 'Resize([640,640])、aspect非保持の正方形変換。CenterCropなし。Train RandomIoUCropは別処理。',
 'COCO dataset PIL RGB/3を期待。reader依存の最終確認が必要。',
 'ConvertPILImage float32 scale=Trueで/255。選択dataloaderにImageNet Normalizeなし（backbone内部の追加処理はUNVERIFIED）。',
 'float32 CHW [0,1]。',
 'COCO原本xywh→dataset/transform XYXY→train ConvertBoxes fmt=cxcywh normalize=True。model output normalized cxcywh。val raw targetはtrain最終形式と同一と仮定しない。',
 'BBox taskではmaskなし。画像との幾何整合はtv_tensors経路で保持。',
 '正常画像empty annotationと位置ラベル付きNG。COCO class remapをReal-IAD8classに変更する必要。',
 'RandomPhotometricDistort .5, ZoomOut, RandomIoUCrop .8, HorizontalFlip、bbox min_size1 sanitize。collate multiscale480..800、epoch71で特定増強停止。',
 '640固定とmultiscaleは別条件。小BBoxをmin_size1で落とす挙動とNG画像意味を検証する。',
 [('rtdetrv2_pytorch/configs/rtdetrv2/include/dataloader.yml','ConvertPILImage'),('rtdetrv2_pytorch/src/data/transforms/_transforms.py','class ConvertBoxes')],
 '選定backbone、最終config継承、backbone内部normalization、RGB reader runtime。')
add('YOLOS','yolos','main eval_size800 / backbone_name tiny',
 'eval: 短辺eval_size、長辺上限eval_size×1333/800、aspect保持。Train tiny scales256..608でdefault eval800と異なる。CenterCropなし。',
 'COCO PIL RGB/3。',IM,
 'ToTensor→Normalize、浮動小数CHW、通常float32。',
 'COCO xywh→絶対XYXY→Normalize transformでnormalized cxcywh。labelsはdataset class体系でadapter確認。',
 'build return_masks=False; maskを使う経路のResizeはnearest。BBox taskでは不要。',
 'COCO positive/empty negative方式。未提供NGを負例にしない。',
 'HorizontalFlip、RandomSelect: RandomResize または Resize400/500/600→RandomSizeCrop384..600→RandomResize。',
 'ViT patch/positional embeddingの実装と選択variantごとの対応は実行前確認。default tinyでも評価サイズは800であり608と決めつけない。',
 [('main.py','--eval_size'),('datasets/coco.py','def make_coco_transforms'),('datasets/transforms.py','class Normalize')],
 'weight/variant固定、tensor dtype設定、位置埋め込み・任意解像度制約の実行。')
add('ViTDet','vitdet','common coco_loader_lsj image_size1024',
 'Train RandomFlip→ResizeScale .1..2.0→FixedSizeCrop1024 pad=False。これはCenterCropではない。Test ResizeShortestEdge1024/max1024。',
 'ViTDet mapper RGB/3。common COCOのBGR設定はViTDetでoverride。',
 'model.pixel_mean/std=constants.imagenet_rgb256_mean/std。0..255スケール用。constants数値は未取得のためUNVERIFIED（名前から数値を推定しない）。',
 'mapper tensor CHW float32、入力0..255をmodel内部でNormalize。0..1用mean/stdをそのまま使わない。',
 'Detectron2 Instances.gt_boxes: XYXY absolute; gt_classes contiguous0..K-1。COCO category_idと同一と仮定しない。',
 'ViTDet標準はMask R-CNN構成を継承しmask headを含む。BBox-only比較にはmask head無効化やlabel供給方針を別途決める必要がある。',
 '位置ラベル付きNG/empty OK。選択recipe filter_emptyのnegative保持方針を確認する。',
 'Large Scale Jitter .1..2.0、random horizontal flip、FixedSizeCrop。recompute_boxes=True。',
 'patch16・window14・画像1024設計。pad/position embedding・解像度変更とmask head構成の実行検証が必要。',
 [('projects/ViTDet/configs/common/coco_loader_lsj.py','image_size'),('configs/common/models/mask_rcnn_vitdet.py','model.pixel_mean'),('detectron2/modeling/meta_arch/rcnn.py','def preprocess_image'),('detectron2/data/dataset_mapper.py','torch.as_tensor')],
 'constantsの数値、選定base/cascade recipeの全継承、BBox-only head、filter_empty、torch/detectron2動作。')
# Korean field-by-field descriptions for the external review package.
for r in records:
 n=r['model']
 r['color_channels']='RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.'
 r['dtype_range_tensor']='uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.'
 r['normalization']=IM+'; ToTensor 이후 적용.'
 r['bbox']='해당 없음: 영상/픽셀 이상 점수 모델. BBox detector와 라벨 형식을 혼용하지 않는다.'
 r['mask']='위치 정답 평가용. 미제공 NG는 유효성 flag=False로 유지하고 0 마스크 정답으로 대체하지 않는다.'
 r['training']='이상탐지 정상 Train만 사용하고 NG는 평가 대상으로 분리한다. 실제 Real-IAD 학습 adapter와 실행은 UNVERIFIED.'
 r['unverified']='최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.'
 if n=='PatchCore':
  r.update(input_resolution='CLI resize=256, imagesize=224',resize_crop='MVTecDataset: 짧은 변256 Resize→CenterCrop224. 정사각 원본에서는896 상당 유지. image/mask Resize 보간을 명시하지 않아 선택 torchvision 버전의 암묵 기본값을 확인해야 한다.',augmentation='선택 MVTecDataset에는 랜덤 기하/색 증강 없음.',resolution_constraints='특징 grid와 memory bank·점수 보정 재구성이 필요. 앞단 공통 Crop을 추가하면 이중 Crop 위험.')
 elif n=='EfficientAD-S':
  r.update(input_resolution='image_size=256, model_size=small',resize_crop='default_transform은256×256 Resize, 기본 CenterCrop 없음. ImageNet penalty의512 Resize→RandomGrayscale→CenterCrop256은 별도 입력 경로.',augmentation='AE 분기 RandomChoice: 밝기/대비/채도 ColorJitter 각각0.2.',resolution_constraints='teacher/student/AE 출력 정렬에 의존. 임의 입력 크기와 anomalib 구현의 차이는 UNVERIFIED.',training='정상 영상으로 teacher/student/AE 학습. ImageNet penalty 기본 경로 none이면 비활성. 외부 데이터와 teacher 가중치는 이번에 받지 않았다.')
 elif n in ['UniAD','HVQ-Trans']:
  r.update(input_resolution='MVTec config input_size=[224,224]',resize_crop='BaseTransformTrain/Test: image BILINEAR, mask NEAREST Resize224. CenterCrop 없음. reader color_mode=RGB.',augmentation='선택 config train hflip/vflip/rotate=False. 정의된 다른 transform의 존재를 활성 증강으로 해석하지 않는다.',resolution_constraints='특징 grid·위치 임베딩·decoder 설정과의 크기 정합을 확인해야 한다. 구형 환경의 Python3.12 실행 UNVERIFIED.',mask='명시적 NEAREST. custom_dataset은 미제공 NG를 전체255로 만드는 경로가 있어 그대로 재사용하면 안 된다.',training='정상 학습 메타파일을 전제하는 재구성 방식. 원격 train.json의 개별 label은 내려받지 않아 UNVERIFIED. 이 프로젝트에서는 정상 Train manifest를 따로 사용한다.')
 elif n in ['Dinomaly','INP-Former']:
  r.update(input_resolution='선택 entry Resize448→CenterCrop392',resize_crop='get_data_transforms: Resize((448,448))→ToTensor→CenterCrop392→Normalize. 정사각 원본896 상당을 유지하지만 원본 Crop 후 Resize와 보간 순서가 다르다.',augmentation='표준 get_data_transforms에는 랜덤 증강 없음. get_strong_transforms의 정의와 실제 선택 entry에서 활성화 여부를 구분한다.',resolution_constraints='DINO 계열 patch14,392=28×14. 임의 크기에서 위치 임베딩·token 정합 실행 확인 필요. 중복 CenterCrop 주의.',mask='GT도 Resize→CenterCrop→ToTensor이며 보간 지정 없음. 마스크 경계 연화/shift와 NEAREST adapter 차이를 별도 검증해야 한다.')
 else:
  r['training']='정상 OK는 객체 없는 negative, 위치 라벨 있는 NG는 positive. 위치 정답 미제공 NG를 빈 라벨 negative로 사용하지 않는다.'
  r['mask']='BBox task에는 픽셀 마스크 입력 불필요. 모델용 라벨과 원본 위치 정답의 유효성은 별도로 보존한다.'
  if n in ['Faster R-CNN','RetinaNet']:
   r.update(input_resolution='기본 생성자 min_size=800, max_size=1333',resize_crop='GeneralizedRCNNTransform: 종횡비 유지, 짧은 변800/긴 변 상한1333 및 batch padding32. CenterCrop 없음. weights factory가 설정을 바꾸는지 별도 확인.',normalization=IM+'; 모델 내부 적용. 외부에서 이중 Normalize 금지.',dtype_range_tensor='RGB list[CHW float Tensor], 입력0..1. normalize는 부동소수 dtype을 요구한다. 실행 AMP/FP16은 UNVERIFIED.',bbox='원본 absolute XYXY float, positive area. labels int64,0 배경/결함1..8. 정상은 boxes shape(0,4)와 빈 labels.',augmentation='생성자 자체에 랜덤 영상 증강 없음. references/detection의 train preset은 recipe별로 달라 최종 선택은 UNVERIFIED.',resolution_constraints='외부512 Resize 후 내부800으로 다시 확대하는 중복 처리 방지 필요. min/max_size를 명시하고 작은 객체 anchor 성능은 실험으로 검증.')
  elif n=='YOLO11':
   r.update(input_resolution='선정 Ultralytics commit 공유 default imgsz640',resize_crop='LetterBox: 종횡비 유지·padding, 명시 기본 INTER_LINEAR, CenterCrop 없음. Train mosaic는 별도 기하 경로.',normalization='선정 detector 학습 경로는 float()/255. ImageNet mean/std Normalize 없음.',dtype_range_tensor='loader BGR→Format의 기본 bgr=0에서 RGB CHW. train float()/255로0..1. predict half 경로가 있으나 실제 FP16 동작 UNVERIFIED.',bbox='YOLO class0..7 + normalized cxcywh. 원본 XYXY는 보존하고 마지막 adapter에서 letterbox scale/offset과 함께 변환.',augmentation='이 commit 공유 default: hsv_h .015/s .7/v .4, translate .1, scale .5, fliplr .5, mosaic1, mixup0/cutmix0. YOLO11 variant별 override는 UNVERIFIED.',resolution_constraints='stride 배수와 rect/letterbox 설정을 확인. 현행 라이브러리 공통 설정이며 YOLO11 최종 variant·고정 release가 확정된 것은 아니다.')
  elif n=='RT-DETRv2':
   r.update(input_resolution='rtdetrv2/include/dataloader.yml:640×640',resize_crop='Resize([640,640]) 정사각 변환, CenterCrop 없음. Train RandomIoUCrop은 별도 처리. 이미지 보간의 라이브러리 암묵 기본값은 버전 고정 후 확인.',normalization='ConvertPILImage float32 scale=True로/255. 선택 dataloader에 ImageNet Normalize 없음. backbone 내부 추가 처리는 UNVERIFIED.',dtype_range_tensor='float32 CHW0..1. RGB reader의 전체 경로 실행은 UNVERIFIED.',bbox='COCO xywh→dataset/transform XYXY→train ConvertBoxes normalized cxcywh. 검증 target을 train 최종 형식과 같다고 가정하지 않는다.',augmentation='PhotometricDistort .5, ZoomOut, IoUCrop .8, HorizontalFlip, min_size1 bbox sanitize. collate 다중 크기480..800, epoch71에서 특정 증강/다중크기 중단.',resolution_constraints='640 고정과 multiscale를 분리. sanitize min_size1이 미세 박스를 제거할 수 있어 NG 의미와 별도 평가해야 한다.')
  elif n=='YOLOS':
   r.update(input_resolution='main eval_size=800, backbone_name=tiny',resize_crop='평가 짧은 변800/긴 변 상한1333. tiny 학습 짧은 변256..608과 다르며 CenterCrop 없음.',bbox='COCO xywh→absolute XYXY→Normalize에서 normalized cxcywh. class ID remap 별도 확인.',augmentation='HorizontalFlip; RandomSelect로 RandomResize 또는 Resize400/500/600→RandomSizeCrop384..600→RandomResize.',resolution_constraints='ViT patch와 위치 임베딩의 임의 크기 제약은 실제 variant에서 UNVERIFIED. tiny 학습608을 평가 기본값으로 단정하지 않는다.',mask='build return_masks=False. 마스크를 쓰는 transform 경로는 nearest 보간이지만 BBox 기본 경로에는 불필요.')
  elif n=='ViTDet':
   r.update(input_resolution='common coco_loader_lsj image_size1024',resize_crop='Train RandomFlip→ResizeScale .1..2.0→FixedSizeCrop1024 pad=False. CenterCrop이 아니다. Test ResizeShortestEdge1024/max1024.',normalization='model.pixel_mean/std=constants.imagenet_rgb256_mean/std (0..255용). constants 숫자 파일은 미수집이므로 수치 자체는 UNVERIFIED.',dtype_range_tensor='mapper CHW tensor는 uint8을 보존할 수 있고 내부 mean/std 연산에서 부동소수로 변환한다. 명시 loader float32는UNVERIFIED. 입력0..255 스케일이다. 0..1용 mean/std와 혼용 금지.',bbox='Instances.gt_boxes absolute XYXY, contiguous gt_classes0..K-1. COCO category_id와 별도 매핑.',mask='기본은 Mask R-CNN head를 포함한다. BBox-only 비교에서는 mask head 비활성화 또는 유효 마스크 학습 정책을 결정해야 한다.',augmentation='Large Scale Jitter .1..2.0, horizontal flip, FixedSizeCrop, recompute_boxes=True.',resolution_constraints='patch16/window14,1024 설계. 크기 변경 시 padding·위치 임베딩·mask head를 검증. filter_empty 설정과 정상 negative 유지 여부도 미확인.')
intro='''# 12개 모델 입력 요구사항 — 커밋 고정 소스 조사

상태는 **정적 소스 확인 VERIFIED / 실제 모델 실행 UNVERIFIED**로 구분한다. 본 프로젝트에서 12개 모델의 최종 라이브러리·variant·가중치·학습 recipe는 확정되지 않았다. 아래는 저자 구현 또는 명시적으로 선정한 구현 후보의 특정 경로이며 모든 구현의 보편 규칙이 아니다. 다운로드한 것은 코드·설정 텍스트뿐이고 가중치·학습·모델 생성은 수행하지 않았다. 표기되지 않은 실행 dtype/보간 기본값은 임의로 확정하지 않는다.

근거의 commit/path/행은 source manifest로 검증한다. COCO/YOLO/torchvision/Detectron2의 클래스 ID와 box 형식을 마지막 adapter에서 분리한다. 원본 absolute XYXY와 이미지 크기는 공통 저장 기준으로 유지한다. NG 위치 정답 미제공은 empty-negative와 다르다. 정상 학습용 이상탐지는 보존된 Train의 OK만 사용하며 Validation/Test NG는 평가에만 쓴다.

## 주요 구현 차이와 공통 전처리 충돌

- PatchCore 256→224 및 Dinomaly/INP-Former 448→392는 정사각형 원본에서 약896 중앙 영역을 유지한다. 별도 CenterCrop을 앞에 추가하면 두 번 잘릴 수 있다. 이번896 crop 수치는 이 기하적 범위를 검토하는 근거이며 보간 순서가 달라 픽셀 결과가 동일하다는 뜻은 아니다.
- torchvision detector 내부 Resize/Normalize와 외부 공통 처리의 중복을 피한다. YOLO/RT-DETR의 /255와 ImageNet Normalize를 동일하게 취급하지 않는다. ViTDet은 0..255 스케일의 내부 normalization을 사용한다.
- 원저자 anomaly loader 일부는 NG mask 부재를 전영역 positive 또는 평가용 0으로 처리한다. 이 프로젝트의 has_mask 정책과 충돌하므로 그대로 재사용하지 않는다.
- mask의 Resize는 binary labeling 목적상 NEAREST 후보를 검토하지만, 저자 구현의 암묵적 보간과 다른 경우 baseline 재현 조건과 공통 adapter 실험 조건을 따로 명시한다.
'''
# Korean, compact field summaries are provided first for team use.
korean={
 'PatchCore':'저자 MVTecDataset, 정상 특징 memory bank. 256→224 중앙 Crop; 원본896 상당. RGB/ImageNet 정규화. 마스크 보간 암묵값과 Real-IAD 결측 마스크 adapter 검증 필요.',
 'EfficientAD-S':'선정 nelson1425 구현. 256 정사각 Resize, 기본 Crop 없음. RGB/ImageNet 정규화. AE 색 증강과 ImageNet penalty 경로를 주 입력과 분리. anomalib 구현과 같다고 가정하지 않음.',
 'UniAD':'저자 MVTec 설정224. 영상 BILINEAR/마스크 NEAREST, RGB/ImageNet 정규화. 미제공 NG를 전체 positive로 만드는 loader 경로 수정 필요.',
 'HVQ-Trans':'저자 MVTec 설정224. UniAD와 유사한 loader 구조지만 별도 commit. 미제공 마스크 처리와 Python3.12 호환성 미검증.',
 'Dinomaly':'저자 Real-IAD single-class 경로448→392. DINO patch14. RGB/ImageNet 정규화. mask 보간과 위치 임베딩을 실행 전 확인.',
 'INP-Former':'저자 single-class 기본448→392. RGB/ImageNet 정규화. 다른 entry/variant를 같은 설정으로 일반화하지 않음.',
 'Faster R-CNN':'torchvision 기본 생성자 단변800/장변1333. RGB float0..1, 내부 ImageNet 정규화. absolute XYXY와 1시작 positive class. weights recipe override 별도 확인.',
 'RetinaNet':'torchvision 기본 생성자800/1333. 내부 정규화·Resize. YOLO 형식이 아닌 absolute XYXY 입력. 작은 객체 anchor와 resize 중복 검증 필요.',
 'YOLO11':'선정 Ultralytics 현행 공통 dataloader640/LetterBox. RGB float/255, normalized cxcywh/0시작 class. YOLO11 variant별 최종 override는 미확정.',
 'RT-DETRv2':'저자 rtdetrv2 dataloader640. float32 scale=True, train normalized cxcywh. collate480..800 및 epoch71 증가 정책 중단. backbone 정규화 추가 여부 미확인.',
 'YOLOS':'저자 main eval_size800. tiny 학습 다중 단변256..608과 평가800을 구분. RGB/ImageNet 정규화, 모델용 normalized cxcywh.',
 'ViTDet':'Detectron2 ViTDet RGB1024 LSJ. 학습 FixedSizeCrop은 CenterCrop이 아님. 0..255 내부 정규화. 기본 mask head와 BBox-only 비교의 충돌 해소 필요.'}
if OUT.exists():
 archive=B/'model_report_previous_draft.md'
 if archive.exists():raise SystemExit('Preserve already archived draft; choose new paths')
 archive.write_text(OUT.read_text())
text=[intro,'| 모델 | 한국어 검토 요약 |','|---|---|']
for r in records:text.append(f'| {r["model"]} | {korean[r["model"]]} |')
fields={'input_resolution':'입력 해상도','resize_crop':'Resize/Crop 및 보간','color_channels':'색상/채널','normalization':'mean/std 및 적용 위치','dtype_range_tensor':'ToTensor·범위·dtype','bbox':'BBox/클래스','mask':'마스크','training':'정상/불량 학습 방식','augmentation':'학습 증강','resolution_constraints':'해상도 변경 제약','unverified':'UNVERIFIED 항목'}
evidence=[]
for r in records:
 manifest=json.loads((B/r['repo_key']/'manifest.json').read_text());r['repo']=manifest['repo'];r['commit']=manifest['commit']
 text.extend([f'## {r["model"]}',f'저장소: https://github.com/{r["repo"]}  \ncommit: `{r["commit"]}`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.'])
 for field,label in fields.items():text.append(f'- **{label}**: {r[field]}')
 for path,needle in r['references']:
  local=B/r['repo_key']/'source'/path
  if local.exists():
   lines=local.read_text().splitlines();line=next((i+1 for i,v in enumerate(lines) if needle in v),None)
   status='VERIFIED' if line else 'UNVERIFIED';url=f'https://github.com/{r["repo"]}/blob/{r["commit"]}/{path}'+(f'#L{line}' if line else '')
   evidence.append(dict(model=r['model'],repo=r['repo'],commit=r['commit'],path=path,symbol=needle,line=line,status=status,sha256=hashlib.sha256(local.read_bytes()).hexdigest(),url=url))
   text.append(f'  - [{path} · {needle} · {status}]({url})')
  else:evidence.append(dict(model=r['model'],path=path,symbol=needle,status='UNVERIFIED'))
OUT.write_text('\n\n'.join(text),encoding='utf-8')
(B/'model_input_fields.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
(B/'model_input_source_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
print('12 models documented; source evidence records',len(evidence))
