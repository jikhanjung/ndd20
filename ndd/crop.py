"""**자르는 틀을 정하는 자리. 여기 하나다.**

두 곳이 이 규칙을 쓴다 — 눈으로 보는 화면(`viewer`)과 지느러미를 세우는
명령(`ndd/commands/fins.py`). 두 벌로 두면 한쪽만 고쳐지고, 그때 화면에서 본
것과 잰 것이 같은 틀 위에 있는지 아무도 모른다.

## 두 가지 틀이 있고 쓰는 데가 다르다

`view_box`  윤곽 바깥틀 + 여백 15%. **눈으로 보려고** 자르는 것이다
`crop_rect` **정사각형** · 상자 긴 변의 `pad` 배. 형제 저장소
            (`finseg/geometry.py`)에서 베껴 온 것으로, **모델이 그 꼴로
            배웠기 때문에** 그대로 맞춰야 한다

베껴 온 쪽의 말을 그대로 옮기면 — *"정사각형을 고집한다. 640 으로 펼 때
가로세로가 다르면 지느러미가 눌리고, 눌린 정도가 상자마다 다르면 모델이 배우는
형태가 흔들린다."* 저쪽은 `pad=2.0` 이 기본인데, 그것은 **지느러미 상자**를
감싸는 값이다. 여기서 우리가 가진 것은 지느러미가 아니라 **돌고래 몸통
폴리곤**이라(`object='dolphin'`), 같은 값을 쓰면 지느러미가 틀 안에서 훨씬
작아진다. **그래서 `pad` 를 재 보고 고른다** — 기본값을 물려받지 않는다.
"""

VIEW_PAD = 0.15                 # 형제 저장소의 `CHIP_PAD` 와 같은 값


def bounds(r):
    """영역의 바깥틀 (x0, y0, x1, y1)."""
    return min(r.xs), min(r.ys), max(r.xs), max(r.ys)


def view_box(r, pad=VIEW_PAD):
    """**보려고** 자르는 틀. 긴 변의 `pad` 만큼을 네 쪽에 두른다."""
    x0, y0, x1, y1 = bounds(r)
    m = max(x1 - x0, y1 - y0) * pad
    return (int(x0 - m), int(y0 - m), int(x1 + m), int(y1 + m))


def crop_rect(box, img_w, img_h, pad):
    """**모델에 넣으려고** 자르는 정사각형 틀. 원본 좌표 (x0, y0, x1, y1).

    형제 저장소 `finseg/geometry.py:crop_rect` 를 그대로 베꼈다.
    가장자리에서는 줄이지 않고 **민다** — 사진보다 큰 정사각형을 요구받을 때만
    사진 크기로 줄인다.
    """
    x1, y1, x2, y2 = box
    side = int(round(max(x2 - x1, y2 - y1) * pad))
    side = min(side, img_w, img_h)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    x0 = max(0, min(int(round(cx - side / 2)), img_w - side))
    y0 = max(0, min(int(round(cy - side / 2)), img_h - side))
    return x0, y0, x0 + side, y0 + side


def gap(r):
    """첫점과 끝점 사이 간격 / 윤곽 크기. 0 에 가까우면 닫힌 것이다.

    **채워도 되는지를 가르는 자다.** 이 값이 크면 채울 때 사람이 안 그린 직선이
    마스크에 들어간다 (`docs/NDD20_자료의_생김새.md`). `ABOVE` 의 3%가 0.1 을
    넘는다 — 그 줄은 성적에서 가른다.
    """
    if len(r.xs) < 2:
        return 0.0
    dx, dy = r.xs[0] - r.xs[-1], r.ys[0] - r.ys[-1]
    size = max(max(r.xs) - min(r.xs), max(r.ys) - min(r.ys)) or 1
    return (dx * dx + dy * dy) ** 0.5 / size


def mask_to_polygon(mask, simplify=0.8):
    """이진 마스크 → 가장 큰 덩어리의 바깥 윤곽. 못 찾으면 (None, 0).

    형제 저장소 `finseg/geometry.py:mask_to_polygon` 을 그대로 베꼈다. 저쪽 말을
    옮기면 — *"가장 큰 것 하나만 쓴다. 물보라나 옆 개체가 딸려 들어온 조각을
    함께 두면 폴리곤이 두 덩어리가 된다."*
    """
    import cv2
    import numpy as np
    m = mask.astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, 0
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) <= 0:
        return None, 0
    if simplify:
        c = cv2.approxPolyDP(c, simplify, True)
    if len(c) < 3:
        return None, 0
    return [(float(p[0][0]), float(p[0][1])) for p in c], int(m.sum())
