# 한글 안내: 기존 YOLO 좌표와 중앙 Crop의 결합 정책을 비교하는 기하 계산을 제공합니다.
# 재현 주의: 주석 변경도 소스 해시를 바꿉니다. 기존 체크포인트는 원래 설정/해시를 확인하고 새 실행과 구분하세요.
"""Post-hoc hybrid extension; primary experiment geometry remains frozen."""
import math

# anchor_union_square: 이름에 해당하는 세부 처리를 수행하며 반환값과 예외는 아래 구현의 계약을 따릅니다.
# 입력 인수: anchor, candidate, width, height.
def anchor_union_square(anchor,candidate,width=1024,height=1024):
    """Smallest shifted in-frame square containing BOTH integer crop rectangles.

    Missing candidate returns the anchor; caller may explicitly choose full fallback.
    No GT pixels or classes enter this construction.
    """
    if candidate is None:return list(anchor)
    x0=min(anchor[0],candidate[0]);y0=min(anchor[1],candidate[1])
    x1=max(anchor[2],candidate[2]);y1=max(anchor[3],candidate[3])
    side=max(x1-x0,y1-y0)
    if side>min(width,height):return [0,0,width,height]
    left=max(0,min(width-side,math.floor((x0+x1-side)/2)))
    top=max(0,min(height-side,math.floor((y0+y1-side)/2)))
    return [left,top,left+side,top+side]
