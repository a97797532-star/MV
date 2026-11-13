# 12개 모델 입력 요구사항 — 커밋 고정 소스 조사

상태는 **정적 소스 확인 VERIFIED / 실제 모델 실행 UNVERIFIED**로 구분한다. 본 프로젝트에서 12개 모델의 최종 라이브러리·variant·가중치·학습 recipe는 확정되지 않았다. 아래는 저자 구현 또는 명시적으로 선정한 구현 후보의 특정 경로이며 모든 구현의 보편 규칙이 아니다. 다운로드한 것은 코드·설정 텍스트뿐이고 가중치·학습·모델 생성은 수행하지 않았다. 표기되지 않은 실행 dtype/보간 기본값은 임의로 확정하지 않는다.

근거의 commit/path/행은 source manifest로 검증한다. COCO/YOLO/torchvision/Detectron2의 클래스 ID와 box 형식을 마지막 adapter에서 분리한다. 원본 absolute XYXY와 이미지 크기는 공통 저장 기준으로 유지한다. NG 위치 정답 미제공은 empty-negative와 다르다. 정상 학습용 이상탐지는 보존된 Train의 OK만 사용하며 Validation/Test NG는 평가에만 쓴다.

## 주요 구현 차이와 공통 전처리 충돌

- PatchCore 256→224 및 Dinomaly/INP-Former 448→392는 정사각형 원본에서 약896 중앙 영역을 유지한다. 별도 CenterCrop을 앞에 추가하면 두 번 잘릴 수 있다. 이번896 crop 수치는 이 기하적 범위를 검토하는 근거이며 보간 순서가 달라 픽셀 결과가 동일하다는 뜻은 아니다.
- torchvision detector 내부 Resize/Normalize와 외부 공통 처리의 중복을 피한다. YOLO/RT-DETR의 /255와 ImageNet Normalize를 동일하게 취급하지 않는다. ViTDet은 0..255 스케일의 내부 normalization을 사용한다.
- 원저자 anomaly loader 일부는 NG mask 부재를 전영역 positive 또는 평가용 0으로 처리한다. 이 프로젝트의 has_mask 정책과 충돌하므로 그대로 재사용하지 않는다.
- mask의 Resize는 binary labeling 목적상 NEAREST 후보를 검토하지만, 저자 구현의 암묵적 보간과 다른 경우 baseline 재현 조건과 공통 adapter 실험 조건을 따로 명시한다.


| 모델 | 한국어 검토 요약 |

|---|---|

| PatchCore | 저자 MVTecDataset, 정상 특징 memory bank. 256→224 중앙 Crop; 원본896 상당. RGB/ImageNet 정규화. 마스크 보간 암묵값과 Real-IAD 결측 마스크 adapter 검증 필요. |

| EfficientAD-S | 선정 nelson1425 구현. 256 정사각 Resize, 기본 Crop 없음. RGB/ImageNet 정규화. AE 색 증강과 ImageNet penalty 경로를 주 입력과 분리. anomalib 구현과 같다고 가정하지 않음. |

| UniAD | 저자 MVTec 설정224. 영상 BILINEAR/마스크 NEAREST, RGB/ImageNet 정규화. 미제공 NG를 전체 positive로 만드는 loader 경로 수정 필요. |

| HVQ-Trans | 저자 MVTec 설정224. UniAD와 유사한 loader 구조지만 별도 commit. 미제공 마스크 처리와 Python3.12 호환성 미검증. |

| Dinomaly | 저자 Real-IAD single-class 경로448→392. DINO patch14. RGB/ImageNet 정규화. mask 보간과 위치 임베딩을 실행 전 확인. |

| INP-Former | 저자 single-class 기본448→392. RGB/ImageNet 정규화. 다른 entry/variant를 같은 설정으로 일반화하지 않음. |

| Faster R-CNN | torchvision 기본 생성자 단변800/장변1333. RGB float0..1, 내부 ImageNet 정규화. absolute XYXY와 1시작 positive class. weights recipe override 별도 확인. |

| RetinaNet | torchvision 기본 생성자800/1333. 내부 정규화·Resize. YOLO 형식이 아닌 absolute XYXY 입력. 작은 객체 anchor와 resize 중복 검증 필요. |

| YOLO11 | 선정 Ultralytics 현행 공통 dataloader640/LetterBox. RGB float/255, normalized cxcywh/0시작 class. YOLO11 variant별 최종 override는 미확정. |

| RT-DETRv2 | 저자 rtdetrv2 dataloader640. float32 scale=True, train normalized cxcywh. collate480..800 및 epoch71 증가 정책 중단. backbone 정규화 추가 여부 미확인. |

| YOLOS | 저자 main eval_size800. tiny 학습 다중 단변256..608과 평가800을 구분. RGB/ImageNet 정규화, 모델용 normalized cxcywh. |

| ViTDet | Detectron2 ViTDet RGB1024 LSJ. 학습 FixedSizeCrop은 CenterCrop이 아님. 0..255 내부 정규화. 기본 mask head와 BBox-only 비교의 충돌 해소 필요. |

## PatchCore

저장소: https://github.com/amazon-science/patchcore-inspection

commit: `fcaa92f124fb1ad74a7acf56726decd4b27cbcad`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: CLI resize=256, imagesize=224

- **Resize/Crop 및 보간**: MVTecDataset: 짧은 변256 Resize→CenterCrop224. 정사각 원본에서는896 상당 유지. image/mask Resize 보간을 명시하지 않아 선택 torchvision 버전의 암묵 기본값을 확인해야 한다.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; ToTensor 이후 적용.

- **ToTensor·범위·dtype**: uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.

- **BBox/클래스**: 해당 없음: 영상/픽셀 이상 점수 모델. BBox detector와 라벨 형식을 혼용하지 않는다.

- **마스크**: 위치 정답 평가용. 미제공 NG는 유효성 flag=False로 유지하고 0 마스크 정답으로 대체하지 않는다.

- **정상/불량 학습 방식**: 이상탐지 정상 Train만 사용하고 NG는 평가 대상으로 분리한다. 실제 Real-IAD 학습 adapter와 실행은 UNVERIFIED.

- **학습 증강**: 선택 MVTecDataset에는 랜덤 기하/색 증강 없음.

- **해상도 변경 제약**: 특징 grid와 memory bank·점수 보정 재구성이 필요. 앞단 공통 Crop을 추가하면 이중 Crop 위험.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [src/patchcore/datasets/mvtec.py · class MVTecDataset · VERIFIED](https://github.com/amazon-science/patchcore-inspection/blob/fcaa92f124fb1ad74a7acf56726decd4b27cbcad/src/patchcore/datasets/mvtec.py#L36)

  - [bin/run_patchcore.py · --resize · VERIFIED](https://github.com/amazon-science/patchcore-inspection/blob/fcaa92f124fb1ad74a7acf56726decd4b27cbcad/bin/run_patchcore.py#L340)

## EfficientAD-S

저장소: https://github.com/nelson1425/EfficientAD

commit: `fcab5146f84ae17597044ad5ddf1656ccf805401`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: image_size=256, model_size=small

- **Resize/Crop 및 보간**: default_transform은256×256 Resize, 기본 CenterCrop 없음. ImageNet penalty의512 Resize→RandomGrayscale→CenterCrop256은 별도 입력 경로.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; ToTensor 이후 적용.

- **ToTensor·범위·dtype**: uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.

- **BBox/클래스**: 해당 없음: 영상/픽셀 이상 점수 모델. BBox detector와 라벨 형식을 혼용하지 않는다.

- **마스크**: 위치 정답 평가용. 미제공 NG는 유효성 flag=False로 유지하고 0 마스크 정답으로 대체하지 않는다.

- **정상/불량 학습 방식**: 정상 영상으로 teacher/student/AE 학습. ImageNet penalty 기본 경로 none이면 비활성. 외부 데이터와 teacher 가중치는 이번에 받지 않았다.

- **학습 증강**: AE 분기 RandomChoice: 밝기/대비/채도 ColorJitter 각각0.2.

- **해상도 변경 제약**: teacher/student/AE 출력 정렬에 의존. 임의 입력 크기와 anomalib 구현의 차이는 UNVERIFIED.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [efficientad.py · image_size = 256 · VERIFIED](https://github.com/nelson1425/EfficientAD/blob/fcab5146f84ae17597044ad5ddf1656ccf805401/efficientad.py#L46)

  - [efficientad.py · default_transform · VERIFIED](https://github.com/nelson1425/EfficientAD/blob/fcab5146f84ae17597044ad5ddf1656ccf805401/efficientad.py#L49)

  - [common.py · class ImageFolderWithoutTarget · VERIFIED](https://github.com/nelson1425/EfficientAD/blob/fcab5146f84ae17597044ad5ddf1656ccf805401/common.py#L103)

## UniAD

저장소: https://github.com/zhiyuanyou/UniAD

commit: `a5b9d9d20c2aae680fa00fe5088616b611e05f3c`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: MVTec config input_size=[224,224]

- **Resize/Crop 및 보간**: BaseTransformTrain/Test: image BILINEAR, mask NEAREST Resize224. CenterCrop 없음. reader color_mode=RGB.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; ToTensor 이후 적용.

- **ToTensor·범위·dtype**: uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.

- **BBox/클래스**: 해당 없음: 영상/픽셀 이상 점수 모델. BBox detector와 라벨 형식을 혼용하지 않는다.

- **마스크**: 명시적 NEAREST. custom_dataset은 미제공 NG를 전체255로 만드는 경로가 있어 그대로 재사용하면 안 된다.

- **정상/불량 학습 방식**: 정상 학습 메타파일을 전제하는 재구성 방식. 원격 train.json의 개별 label은 내려받지 않아 UNVERIFIED. 이 프로젝트에서는 정상 Train manifest를 따로 사용한다.

- **학습 증강**: 선택 config train hflip/vflip/rotate=False. 정의된 다른 transform의 존재를 활성 증강으로 해석하지 않는다.

- **해상도 변경 제약**: 특징 grid·위치 임베딩·decoder 설정과의 크기 정합을 확인해야 한다. 구형 환경의 Python3.12 실행 UNVERIFIED.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [experiments/MVTec-AD/config.yaml · input_size · VERIFIED](https://github.com/zhiyuanyou/UniAD/blob/a5b9d9d20c2aae680fa00fe5088616b611e05f3c/experiments/MVTec-AD/config.yaml#L24)

  - [datasets/base_dataset.py · class TrainBaseTransform · VERIFIED](https://github.com/zhiyuanyou/UniAD/blob/a5b9d9d20c2aae680fa00fe5088616b611e05f3c/datasets/base_dataset.py#L27)

  - [datasets/custom_dataset.py · np.ones · VERIFIED](https://github.com/zhiyuanyou/UniAD/blob/a5b9d9d20c2aae680fa00fe5088616b611e05f3c/datasets/custom_dataset.py#L121)

  - [datasets/image_reader.py · RGB · VERIFIED](https://github.com/zhiyuanyou/UniAD/blob/a5b9d9d20c2aae680fa00fe5088616b611e05f3c/datasets/image_reader.py#L10)

## HVQ-Trans

저장소: https://github.com/RuiyingLu/HVQ-Trans

commit: `12fbfa96b906d1462cbfc1787e47e2fc17468134`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: MVTec config input_size=[224,224]

- **Resize/Crop 및 보간**: BaseTransformTrain/Test: image BILINEAR, mask NEAREST Resize224. CenterCrop 없음. reader color_mode=RGB.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; ToTensor 이후 적용.

- **ToTensor·범위·dtype**: uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.

- **BBox/클래스**: 해당 없음: 영상/픽셀 이상 점수 모델. BBox detector와 라벨 형식을 혼용하지 않는다.

- **마스크**: 명시적 NEAREST. custom_dataset은 미제공 NG를 전체255로 만드는 경로가 있어 그대로 재사용하면 안 된다.

- **정상/불량 학습 방식**: 정상 학습 메타파일을 전제하는 재구성 방식. 원격 train.json의 개별 label은 내려받지 않아 UNVERIFIED. 이 프로젝트에서는 정상 Train manifest를 따로 사용한다.

- **학습 증강**: 선택 config train hflip/vflip/rotate=False. 정의된 다른 transform의 존재를 활성 증강으로 해석하지 않는다.

- **해상도 변경 제약**: 특징 grid·위치 임베딩·decoder 설정과의 크기 정합을 확인해야 한다. 구형 환경의 Python3.12 실행 UNVERIFIED.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [experiments/MVTec-AD/config.yaml · input_size · VERIFIED](https://github.com/RuiyingLu/HVQ-Trans/blob/12fbfa96b906d1462cbfc1787e47e2fc17468134/experiments/MVTec-AD/config.yaml#L24)

  - [datasets/base_dataset.py · class TrainBaseTransform · VERIFIED](https://github.com/RuiyingLu/HVQ-Trans/blob/12fbfa96b906d1462cbfc1787e47e2fc17468134/datasets/base_dataset.py#L27)

  - [datasets/custom_dataset.py · np.ones · VERIFIED](https://github.com/RuiyingLu/HVQ-Trans/blob/12fbfa96b906d1462cbfc1787e47e2fc17468134/datasets/custom_dataset.py#L134)

  - [datasets/image_reader.py · RGB · VERIFIED](https://github.com/RuiyingLu/HVQ-Trans/blob/12fbfa96b906d1462cbfc1787e47e2fc17468134/datasets/image_reader.py#L10)

## Dinomaly

저장소: https://github.com/guojiajeremy/Dinomaly

commit: `1f252be03a918789b19848f0ca37166e7c28dada`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: 선택 entry Resize448→CenterCrop392

- **Resize/Crop 및 보간**: get_data_transforms: Resize((448,448))→ToTensor→CenterCrop392→Normalize. 정사각 원본896 상당을 유지하지만 원본 Crop 후 Resize와 보간 순서가 다르다.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; ToTensor 이후 적용.

- **ToTensor·범위·dtype**: uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.

- **BBox/클래스**: 해당 없음: 영상/픽셀 이상 점수 모델. BBox detector와 라벨 형식을 혼용하지 않는다.

- **마스크**: GT도 Resize→CenterCrop→ToTensor이며 보간 지정 없음. 마스크 경계 연화/shift와 NEAREST adapter 차이를 별도 검증해야 한다.

- **정상/불량 학습 방식**: 이상탐지 정상 Train만 사용하고 NG는 평가 대상으로 분리한다. 실제 Real-IAD 학습 adapter와 실행은 UNVERIFIED.

- **학습 증강**: 표준 get_data_transforms에는 랜덤 증강 없음. get_strong_transforms의 정의와 실제 선택 entry에서 활성화 여부를 구분한다.

- **해상도 변경 제약**: DINO 계열 patch14,392=28×14. 임의 크기에서 위치 임베딩·token 정합 실행 확인 필요. 중복 CenterCrop 주의.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [dataset.py · def get_data_transforms · VERIFIED](https://github.com/guojiajeremy/Dinomaly/blob/1f252be03a918789b19848f0ca37166e7c28dada/dataset.py#L19)

  - [dinomaly_realiad_sep.py · crop_size · VERIFIED](https://github.com/guojiajeremy/Dinomaly/blob/1f252be03a918789b19848f0ca37166e7c28dada/dinomaly_realiad_sep.py#L82)

  - [dinomaly_realiad_sep.py · 448 · VERIFIED](https://github.com/guojiajeremy/Dinomaly/blob/1f252be03a918789b19848f0ca37166e7c28dada/dinomaly_realiad_sep.py#L81)

## INP-Former

저장소: https://github.com/luow23/INP-Former

commit: `17d265381d9b323a2ef6e05aab0665a85edebe84`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: 선택 entry Resize448→CenterCrop392

- **Resize/Crop 및 보간**: get_data_transforms: Resize((448,448))→ToTensor→CenterCrop392→Normalize. 정사각 원본896 상당을 유지하지만 원본 Crop 후 Resize와 보간 순서가 다르다.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; ToTensor 이후 적용.

- **ToTensor·범위·dtype**: uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.

- **BBox/클래스**: 해당 없음: 영상/픽셀 이상 점수 모델. BBox detector와 라벨 형식을 혼용하지 않는다.

- **마스크**: GT도 Resize→CenterCrop→ToTensor이며 보간 지정 없음. 마스크 경계 연화/shift와 NEAREST adapter 차이를 별도 검증해야 한다.

- **정상/불량 학습 방식**: 이상탐지 정상 Train만 사용하고 NG는 평가 대상으로 분리한다. 실제 Real-IAD 학습 adapter와 실행은 UNVERIFIED.

- **학습 증강**: 표준 get_data_transforms에는 랜덤 증강 없음. get_strong_transforms의 정의와 실제 선택 entry에서 활성화 여부를 구분한다.

- **해상도 변경 제약**: DINO 계열 patch14,392=28×14. 임의 크기에서 위치 임베딩·token 정합 실행 확인 필요. 중복 CenterCrop 주의.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [dataset.py · def get_data_transforms · VERIFIED](https://github.com/luow23/INP-Former/blob/17d265381d9b323a2ef6e05aab0665a85edebe84/dataset.py#L19)

  - [INP_Former_Single_Class.py · crop_size · VERIFIED](https://github.com/luow23/INP-Former/blob/17d265381d9b323a2ef6e05aab0665a85edebe84/INP_Former_Single_Class.py#L30)

  - [INP_Former_Single_Class.py · 448 · VERIFIED](https://github.com/luow23/INP-Former/blob/17d265381d9b323a2ef6e05aab0665a85edebe84/INP_Former_Single_Class.py#L166)

## Faster R-CNN

저장소: https://github.com/pytorch/vision

commit: `4260301135e34180d865426765487113f84e7707`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: 기본 생성자 min_size=800, max_size=1333

- **Resize/Crop 및 보간**: GeneralizedRCNNTransform: 종횡비 유지, 짧은 변800/긴 변 상한1333 및 batch padding32. CenterCrop 없음. weights factory가 설정을 바꾸는지 별도 확인.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; 모델 내부 적용. 외부에서 이중 Normalize 금지.

- **ToTensor·범위·dtype**: RGB list[CHW float Tensor], 입력0..1. normalize는 부동소수 dtype을 요구한다. 실행 AMP/FP16은 UNVERIFIED.

- **BBox/클래스**: 원본 absolute XYXY float, positive area. labels int64,0 배경/결함1..8. 정상은 boxes shape(0,4)와 빈 labels.

- **마스크**: BBox task에는 픽셀 마스크 입력 불필요. 모델용 라벨과 원본 위치 정답의 유효성은 별도로 보존한다.

- **정상/불량 학습 방식**: 정상 OK는 객체 없는 negative, 위치 라벨 있는 NG는 positive. 위치 정답 미제공 NG를 빈 라벨 negative로 사용하지 않는다.

- **학습 증강**: 생성자 자체에 랜덤 영상 증강 없음. references/detection의 train preset은 recipe별로 달라 최종 선택은 UNVERIFIED.

- **해상도 변경 제약**: 외부512 Resize 후 내부800으로 다시 확대하는 중복 처리 방지 필요. min/max_size를 명시하고 작은 객체 anchor 성능은 실험으로 검증.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [torchvision/models/detection/faster_rcnn.py · min_size=800 · VERIFIED](https://github.com/pytorch/vision/blob/4260301135e34180d865426765487113f84e7707/torchvision/models/detection/faster_rcnn.py#L172)

  - [torchvision/models/detection/transform.py · def normalize · VERIFIED](https://github.com/pytorch/vision/blob/4260301135e34180d865426765487113f84e7707/torchvision/models/detection/transform.py#L160)

  - [torchvision/models/detection/transform.py · mode="bilinear" · VERIFIED](https://github.com/pytorch/vision/blob/4260301135e34180d865426765487113f84e7707/torchvision/models/detection/transform.py#L69)

## RetinaNet

저장소: https://github.com/pytorch/vision

commit: `4260301135e34180d865426765487113f84e7707`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: 기본 생성자 min_size=800, max_size=1333

- **Resize/Crop 및 보간**: GeneralizedRCNNTransform: 종횡비 유지, 짧은 변800/긴 변 상한1333 및 batch padding32. CenterCrop 없음. weights factory가 설정을 바꾸는지 별도 확인.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; 모델 내부 적용. 외부에서 이중 Normalize 금지.

- **ToTensor·범위·dtype**: RGB list[CHW float Tensor], 입력0..1. normalize는 부동소수 dtype을 요구한다. 실행 AMP/FP16은 UNVERIFIED.

- **BBox/클래스**: 원본 absolute XYXY float, positive area. labels int64,0 배경/결함1..8. 정상은 boxes shape(0,4)와 빈 labels.

- **마스크**: BBox task에는 픽셀 마스크 입력 불필요. 모델용 라벨과 원본 위치 정답의 유효성은 별도로 보존한다.

- **정상/불량 학습 방식**: 정상 OK는 객체 없는 negative, 위치 라벨 있는 NG는 positive. 위치 정답 미제공 NG를 빈 라벨 negative로 사용하지 않는다.

- **학습 증강**: 생성자 자체에 랜덤 영상 증강 없음. references/detection의 train preset은 recipe별로 달라 최종 선택은 UNVERIFIED.

- **해상도 변경 제약**: 외부512 Resize 후 내부800으로 다시 확대하는 중복 처리 방지 필요. min/max_size를 명시하고 작은 객체 anchor 성능은 실험으로 검증.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [torchvision/models/detection/retinanet.py · min_size=800 · VERIFIED](https://github.com/pytorch/vision/blob/4260301135e34180d865426765487113f84e7707/torchvision/models/detection/retinanet.py#L422)

  - [torchvision/models/detection/transform.py · def normalize · VERIFIED](https://github.com/pytorch/vision/blob/4260301135e34180d865426765487113f84e7707/torchvision/models/detection/transform.py#L160)

  - [torchvision/models/detection/transform.py · mode="bilinear" · VERIFIED](https://github.com/pytorch/vision/blob/4260301135e34180d865426765487113f84e7707/torchvision/models/detection/transform.py#L69)

## YOLO11

저장소: https://github.com/ultralytics/ultralytics

commit: `d2b7876e79ad2e02fd77221622774b511a8f0cb3`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: 선정 Ultralytics commit 공유 default imgsz640

- **Resize/Crop 및 보간**: LetterBox: 종횡비 유지·padding, 명시 기본 INTER_LINEAR, CenterCrop 없음. Train mosaic는 별도 기하 경로.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: 선정 detector 학습 경로는 float()/255. ImageNet mean/std Normalize 없음.

- **ToTensor·범위·dtype**: loader BGR→Format의 기본 bgr=0에서 RGB CHW. train float()/255로0..1. predict half 경로가 있으나 실제 FP16 동작 UNVERIFIED.

- **BBox/클래스**: YOLO class0..7 + normalized cxcywh. 원본 XYXY는 보존하고 마지막 adapter에서 letterbox scale/offset과 함께 변환.

- **마스크**: BBox task에는 픽셀 마스크 입력 불필요. 모델용 라벨과 원본 위치 정답의 유효성은 별도로 보존한다.

- **정상/불량 학습 방식**: 정상 OK는 객체 없는 negative, 위치 라벨 있는 NG는 positive. 위치 정답 미제공 NG를 빈 라벨 negative로 사용하지 않는다.

- **학습 증강**: 이 commit 공유 default: hsv_h .015/s .7/v .4, translate .1, scale .5, fliplr .5, mosaic1, mixup0/cutmix0. YOLO11 variant별 override는 UNVERIFIED.

- **해상도 변경 제약**: stride 배수와 rect/letterbox 설정을 확인. 현행 라이브러리 공통 설정이며 YOLO11 최종 variant·고정 release가 확정된 것은 아니다.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [ultralytics/cfg/default.yaml · imgsz: · VERIFIED](https://github.com/ultralytics/ultralytics/blob/d2b7876e79ad2e02fd77221622774b511a8f0cb3/ultralytics/cfg/default.yaml#L16)

  - [ultralytics/data/augment.py · class LetterBox · VERIFIED](https://github.com/ultralytics/ultralytics/blob/d2b7876e79ad2e02fd77221622774b511a8f0cb3/ultralytics/data/augment.py#L1678)

  - [ultralytics/data/augment.py · class Format · VERIFIED](https://github.com/ultralytics/ultralytics/blob/d2b7876e79ad2e02fd77221622774b511a8f0cb3/ultralytics/data/augment.py#L2328)

  - [ultralytics/models/yolo/detect/train.py · preprocess_batch · VERIFIED](https://github.com/ultralytics/ultralytics/blob/d2b7876e79ad2e02fd77221622774b511a8f0cb3/ultralytics/models/yolo/detect/train.py#L37)

## RT-DETRv2

저장소: https://github.com/lyuwenyu/RT-DETR

commit: `df2a96c8c3a098567a1149bf0248da6efe6d495d`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: rtdetrv2/include/dataloader.yml:640×640

- **Resize/Crop 및 보간**: Resize([640,640]) 정사각 변환, CenterCrop 없음. Train RandomIoUCrop은 별도 처리. 이미지 보간의 라이브러리 암묵 기본값은 버전 고정 후 확인.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: ConvertPILImage float32 scale=True로/255. 선택 dataloader에 ImageNet Normalize 없음. backbone 내부 추가 처리는 UNVERIFIED.

- **ToTensor·범위·dtype**: float32 CHW0..1. RGB reader의 전체 경로 실행은 UNVERIFIED.

- **BBox/클래스**: COCO xywh→dataset/transform XYXY→train ConvertBoxes normalized cxcywh. 검증 target을 train 최종 형식과 같다고 가정하지 않는다.

- **마스크**: BBox task에는 픽셀 마스크 입력 불필요. 모델용 라벨과 원본 위치 정답의 유효성은 별도로 보존한다.

- **정상/불량 학습 방식**: 정상 OK는 객체 없는 negative, 위치 라벨 있는 NG는 positive. 위치 정답 미제공 NG를 빈 라벨 negative로 사용하지 않는다.

- **학습 증강**: PhotometricDistort .5, ZoomOut, IoUCrop .8, HorizontalFlip, min_size1 bbox sanitize. collate 다중 크기480..800, epoch71에서 특정 증강/다중크기 중단.

- **해상도 변경 제약**: 640 고정과 multiscale를 분리. sanitize min_size1이 미세 박스를 제거할 수 있어 NG 의미와 별도 평가해야 한다.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [rtdetrv2_pytorch/configs/rtdetrv2/include/dataloader.yml · ConvertPILImage · VERIFIED](https://github.com/lyuwenyu/RT-DETR/blob/df2a96c8c3a098567a1149bf0248da6efe6d495d/rtdetrv2_pytorch/configs/rtdetrv2/include/dataloader.yml#L13)

  - [rtdetrv2_pytorch/src/data/transforms/_transforms.py · class ConvertBoxes · VERIFIED](https://github.com/lyuwenyu/RT-DETR/blob/df2a96c8c3a098567a1149bf0248da6efe6d495d/rtdetrv2_pytorch/src/data/transforms/_transforms.py#L101)

## YOLOS

저장소: https://github.com/hustvl/YOLOS

commit: `5717fc29d727dab84ad585c56457b4de1225eddc`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: main eval_size=800, backbone_name=tiny

- **Resize/Crop 및 보간**: 평가 짧은 변800/긴 변 상한1333. tiny 학습 짧은 변256..608과 다르며 CenterCrop 없음.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]; ToTensor 이후 적용.

- **ToTensor·범위·dtype**: uint8 영상에서 ToTensor로 CHW/0..1 부동소수 변환 후 정규화. 보통 float32이나 실행 시 기본 dtype·AMP 설정은 UNVERIFIED.

- **BBox/클래스**: COCO xywh→absolute XYXY→Normalize에서 normalized cxcywh. class ID remap 별도 확인.

- **마스크**: build return_masks=False. 마스크를 쓰는 transform 경로는 nearest 보간이지만 BBox 기본 경로에는 불필요.

- **정상/불량 학습 방식**: 정상 OK는 객체 없는 negative, 위치 라벨 있는 NG는 positive. 위치 정답 미제공 NG를 빈 라벨 negative로 사용하지 않는다.

- **학습 증강**: HorizontalFlip; RandomSelect로 RandomResize 또는 Resize400/500/600→RandomSizeCrop384..600→RandomResize.

- **해상도 변경 제약**: ViT patch와 위치 임베딩의 임의 크기 제약은 실제 variant에서 UNVERIFIED. tiny 학습608을 평가 기본값으로 단정하지 않는다.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [main.py · --eval_size · VERIFIED](https://github.com/hustvl/YOLOS/blob/5717fc29d727dab84ad585c56457b4de1225eddc/main.py#L30)

  - [datasets/coco.py · def make_coco_transforms · VERIFIED](https://github.com/hustvl/YOLOS/blob/5717fc29d727dab84ad585c56457b4de1225eddc/datasets/coco.py#L130)

  - [datasets/transforms.py · class Normalize · VERIFIED](https://github.com/hustvl/YOLOS/blob/5717fc29d727dab84ad585c56457b4de1225eddc/datasets/transforms.py#L261)

## ViTDet

저장소: https://github.com/facebookresearch/detectron2

commit: `247691a1c292654867deb35cabb27f18d75a1363`. 정적 소스 VERIFIED; 모델 실행·성능 UNVERIFIED.

- **입력 해상도**: common coco_loader_lsj image_size1024

- **Resize/Crop 및 보간**: Train RandomFlip→ResizeScale .1..2.0→FixedSizeCrop1024 pad=False. CenterCrop이 아니다. Test ResizeShortestEdge1024/max1024.

- **색상/채널**: RGB 3채널. 입력 로더의 변환과 최종 tensor 채널 순서를 adapter에서 검증한다.

- **mean/std 및 적용 위치**: model.pixel_mean/std=constants.imagenet_rgb256_mean/std (0..255용). constants 숫자 파일은 미수집이므로 수치 자체는 UNVERIFIED.

- **ToTensor·범위·dtype**: mapper는 CHW tensor를 만들며 uint8을 보존할 수 있다. 모델 내부 mean/std 연산에서 부동소수로 변환된다. 명시적 float32 loader 변환은 확인되지 않아 UNVERIFIED. 입력은0..255 스케일이다. 0..1용 mean/std와 혼용 금지.

- **BBox/클래스**: Instances.gt_boxes absolute XYXY, contiguous gt_classes0..K-1. COCO category_id와 별도 매핑.

- **마스크**: 기본은 Mask R-CNN head를 포함한다. BBox-only 비교에서는 mask head 비활성화 또는 유효 마스크 학습 정책을 결정해야 한다.

- **정상/불량 학습 방식**: 정상 OK는 객체 없는 negative, 위치 라벨 있는 NG는 positive. 위치 정답 미제공 NG를 빈 라벨 negative로 사용하지 않는다.

- **학습 증강**: Large Scale Jitter .1..2.0, horizontal flip, FixedSizeCrop, recompute_boxes=True.

- **해상도 변경 제약**: patch16/window14,1024 설계. 크기 변경 시 padding·위치 임베딩·mask head를 검증. filter_empty 설정과 정상 negative 유지 여부도 미확인.

- **UNVERIFIED 항목**: 최종 variant·가중치·의존 라이브러리 버전·실행 dtype/보간·해상도 변경 시 모델 성능은 UNVERIFIED.

  - [projects/ViTDet/configs/common/coco_loader_lsj.py · image_size · VERIFIED](https://github.com/facebookresearch/detectron2/blob/247691a1c292654867deb35cabb27f18d75a1363/projects/ViTDet/configs/common/coco_loader_lsj.py#L6)

  - [configs/common/models/mask_rcnn_vitdet.py · model.pixel_mean · VERIFIED](https://github.com/facebookresearch/detectron2/blob/247691a1c292654867deb35cabb27f18d75a1363/configs/common/models/mask_rcnn_vitdet.py#L10)

  - [detectron2/modeling/meta_arch/rcnn.py · def preprocess_image · VERIFIED](https://github.com/facebookresearch/detectron2/blob/247691a1c292654867deb35cabb27f18d75a1363/detectron2/modeling/meta_arch/rcnn.py#L223)

  - [detectron2/data/dataset_mapper.py · torch.as_tensor · VERIFIED](https://github.com/facebookresearch/detectron2/blob/247691a1c292654867deb35cabb27f18d75a1363/detectron2/data/dataset_mapper.py#L171)