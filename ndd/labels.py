"""**NDD20 라벨을 읽는 자리. 여기 하나다.**

원본은 VIA(VGG Image Annotator) 가 뱉은 JSON 두 개다.

    ABOVE_LABELS.json   수면 위 · 등지느러미 폴리라인 · 종 · 일부에 개체 ID
    BELOW_LABELS.json   수중 · 몸통 · 초점 여부 · 대부분에 개체 ID

`{"<파일명><크기>": {"filename", "size", "regions": [...]}}` 꼴이고, 영역마다
`shape_attributes`(폴리라인 좌표)와 `region_attributes`(종·개체 ID 따위)가 있다.

## 왜 파서를 한 곳에 두나

형제 저장소(`dolfinserver2`)가 판정 규칙·좌표 사상·비교 계산을 한 자리씩에
둔 것과 같은 이유다 — **두 벌로 두면 한쪽만 고쳐지고, 그때 어느 쪽 숫자가
맞는지 아무도 모른다.** 여기서는 특히 **무엇을 "개체 ID 가 있다" 로 볼지**가
그렇다: 빈 문자열·공백만 든 것이 섞여 있어, 세는 자리마다 달리 처리하면
개체 수가 자리마다 달라진다.

## 이 자료에 대해 알고 시작할 것

- **날짜가 없다.** `file_attributes` 가 비어 있고 파일명이 일련번호이며
  **EXIF 도 지워져 있다.** 형제 저장소가 성적에 붙이는 첫 규칙(날로 가르기)을
  여기서는 못 쓴다 — `ndd.split` 이 그 뜻을 다시 적는다
- **수면 위는 개체 ID 가 얇다.** 영역 2,939 중 424(14%)에만 붙어 있다
- **수중은 다른 문제다.** 등지느러미 뒷날이 아니라 몸통 무늬를 본다
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# 기본 자리. `NDD20_DIR` 로 대 준다 — 기계마다 NAS 를 보는 길이 다르다
# (형제 저장소의 `finseg/nas.py` 가 같은 일을 한다).
DEFAULT_DIR = Path(os.environ.get(
    "NDD20_DIR", "/nas/JikhanJung/DolFinID/DolFinID from dropbox/NDD20"))

SETS = ("ABOVE", "BELOW")


@dataclass
class Region:
    """영역 하나 — 사진 한 장 안의 돌고래 하나."""

    image: str                      # 파일 이름 (`104.jpg`)
    kind: str                       # ABOVE · BELOW
    shape: str                      # polyline · polygon …
    xs: list = field(default_factory=list)
    ys: list = field(default_factory=list)
    species: str = ""               # BND · WBD (ABOVE 만)
    ind: str = ""                   # 개체 ID. **없으면 빈 문자열이다**
    attrs: dict = field(default_factory=dict)

    @property
    def labelled(self):
        """개체 ID 가 있나. **여기 하나가 그것을 정한다.**"""
        return bool(self.ind)


def _ind_of(attrs):
    """`region_attributes` 에서 개체 ID 를 꺼낸다.

    **빈 문자열과 공백만 든 것을 '없음' 으로 본다.** VIA 는 칸을 만들어 두고
    비워 두는 일이 흔해서, 그냥 `'id' in attrs` 로 세면 없는 것을 있다고 센다.
    """
    v = attrs.get("id", "")
    return str(v).strip() if v is not None else ""


def load(kind, root=None):
    """한 갈래의 영역 전부. 사진 차례는 파일이 든 차례 그대로다."""
    if kind not in SETS:
        raise ValueError(f"ABOVE · BELOW 중 하나라야 한다: {kind}")
    root = Path(root or DEFAULT_DIR)
    f = root / f"{kind}_LABELS.json"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} 가 없다 — `NDD20_DIR` 를 자료 자리로 대 줄 것")
    raw = json.loads(f.read_text())
    out = []
    for v in raw.values():
        name = v["filename"]
        for r in (v.get("regions") or []):
            sa = r.get("shape_attributes") or {}
            ra = r.get("region_attributes") or {}
            out.append(Region(
                image=name, kind=kind, shape=sa.get("name", ""),
                xs=list(sa.get("all_points_x") or []),
                ys=list(sa.get("all_points_y") or []),
                species=str(ra.get("species", "") or ""),
                ind=_ind_of(ra), attrs=dict(ra)))
    return out


def images(kind, root=None):
    """그 갈래의 사진 파일 자리. 없는 것은 안 낸다."""
    root = Path(root or DEFAULT_DIR)
    d = root / kind
    if not d.is_dir():
        raise FileNotFoundError(f"{d} 가 없다")
    return {p.name: p for p in sorted(d.iterdir()) if p.suffix.lower() in
            (".jpg", ".jpeg", ".png")}
