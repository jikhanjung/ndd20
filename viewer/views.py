"""**NDD20 을 눈으로 보는 화면.** 보기만 한다 — 받는 것이 없다.

    /                      격자. **한 칸이 지느러미 하나**다
    /ind/<개체>             한 개체의 것만 모아 본다 (re-ID 를 눈으로 보는 자리)
    /img/<갈래>/<영역>       그 영역만 잘라 낸 그림 (캐시)

## 사진이 아니라 **영역**이 단위다

원본은 5184×3456 인데 지느러미는 그 안의 한 뼘이다. 사진째 보면 정작 볼 것이
안 보이고 내려보내는 값만 든다. 그래서 **윤곽의 바깥틀에 여백을 둘러 잘라
낸다** — 형제 저장소가 상자마다 640 크롭을 두는 것과 같은 까닭이다.

## 윤곽은 서버가 안 그린다

좌표를 **잘라 낸 틀 기준 0~1** 로 내려보내고 브라우저가 SVG 로 얹는다.
켜고 끌 수 있어야 하고, 서버가 구워 버리면 그림과 좌표가 갈렸을 때 어느 쪽이
틀렸는지 못 가린다.
"""
import io
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render

from ndd import labels

PAD = 0.15                      # 바깥틀 대비 여백. 형제 저장소의 `CHIP_PAD` 와 같은 값
_CACHE = {}


def _regions(kind):
    """갈래 하나의 영역에 **번호를 붙여** 들고 있는다.

    라벨 JSON 이 6~9MB라 요청마다 읽으면 그 자체가 값이다 (형제 저장소가 격자를
    요청마다 다시 읽다 1.1초를 물던 것과 같은 종류다). 번호는 `<파일명>~<몇째>`
    라 **자료가 안 바뀌는 한 고정**이고, 주소에 그대로 쓴다.
    """
    if kind not in _CACHE:
        regs = labels.load(kind, settings.NDD20_DIR)
        seen = {}
        out = []
        for r in regs:
            i = seen.get(r.image, 0)
            seen[r.image] = i + 1
            # **`#` 를 쓰지 않는다** — URL 에서 조각 구분자라 서버까지 안 간다
            # (브라우저에서도 똑같이 깨진다). `~` 는 경로에 그대로 실린다
            out.append((f"{r.image}~{i}", r))
        _CACHE[kind] = (out, {k: r for k, r in out})
    return _CACHE[kind]


def _box(r, pad=PAD):
    """윤곽의 바깥틀 + 여백 → 자를 틀 (x0, y0, x1, y1). 정수다."""
    x0, x1 = min(r.xs), max(r.xs)
    y0, y1 = min(r.ys), max(r.ys)
    m = max(x1 - x0, y1 - y0) * pad
    return (int(x0 - m), int(y0 - m), int(x1 + m), int(y1 + m))


def _card(key, r):
    """격자 한 칸. **좌표는 자를 틀 기준 0~1** 이라 크기에 안 매인다."""
    x0, y0, x1, y1 = _box(r)
    w = max(1, x1 - x0), max(1, y1 - y0)
    return {
        "key": key, "image": r.image, "ind": r.ind, "species": r.species,
        "labelled": r.labelled, "n_pts": len(r.xs),
        "pts": " ".join(f"{(x - x0) / w[0]:.4f},{(y - y0) / w[1]:.4f}"
                        for x, y in zip(r.xs, r.ys)),
        # **닫히지 않은 것을 표로 단다.** 채울 때 없는 직선을 지어 넣게 되는
        # 것들이라(ABOVE 의 3%), 성적에서 가를 줄이기도 하다
        "gap": round(_gap(r), 3),
    }


def _gap(r):
    """첫점과 끝점 사이 간격 / 윤곽 크기. 0 에 가까우면 닫힌 것이다."""
    if len(r.xs) < 2:
        return 0.0
    dx = r.xs[0] - r.xs[-1]
    dy = r.ys[0] - r.ys[-1]
    size = max(max(r.xs) - min(r.xs), max(r.ys) - min(r.ys)) or 1
    return (dx * dx + dy * dy) ** 0.5 / size


def index(request):
    kind = request.GET.get("set", "ABOVE")
    if kind not in labels.SETS:
        kind = "ABOVE"
    only = request.GET.get("only", "")            # "" · id · noid · open
    species = request.GET.get("species", "")
    page = max(1, int(request.GET.get("page", 1) or 1))
    per = min(300, max(12, int(request.GET.get("n", 60) or 60)))

    regs, _ = _regions(kind)
    sel = []
    for key, r in regs:
        if only == "id" and not r.labelled:
            continue
        if only == "noid" and r.labelled:
            continue
        if only == "open" and _gap(r) <= 0.1:
            continue
        if species and r.species != species:
            continue
        sel.append((key, r))

    n_all = len(sel)
    shown = sel[(page - 1) * per:(page - 1) * per + per]
    return render(request, "viewer/index.html", {
        "kind": kind, "sets": labels.SETS, "only": only, "species": species,
        "all_species": sorted({r.species for _, r in regs if r.species}),
        "page": page, "per": per, "n_all": n_all,
        "n_pages": max(1, -(-n_all // per)),
        "cards": [_card(k, r) for k, r in shown],
        "n_labelled": sum(1 for _, r in sel if r.labelled),
        "n_open": sum(1 for _, r in sel if _gap(r) > 0.1),
        "inds": sorted({r.ind for _, r in regs if r.labelled}),
    })


def individual(request, ind):
    """한 개체의 것만 모아 본다 — **re-ID 를 눈으로 보는 자리**다.

    같은 개체가 정말 같아 보이는지, 몇 장이 거의 같은 그림(연사)인지가 여기서
    눈에 띈다. **날짜가 없어 연사를 자료로는 못 가르는 자리**라(`CLAUDE.md`),
    사람 눈이 그것을 처음 보는 곳이 여기다.
    """
    kind = request.GET.get("set", "ABOVE")
    if kind not in labels.SETS:
        raise Http404
    regs, _ = _regions(kind)
    sel = [(k, r) for k, r in regs if r.ind == ind]
    if not sel:
        raise Http404(f"{kind} 에 개체 {ind} 이 없다")
    return render(request, "viewer/ind.html", {
        "kind": kind, "ind": ind, "cards": [_card(k, r) for k, r in sel],
        "n": len(sel),
        "inds": sorted({r.ind for _, r in regs if r.labelled}),
    })


def image(request, kind, key):
    """그 영역만 잘라 낸 그림. 한 번 만들어 `out/crops/` 에 둔다."""
    if kind not in labels.SETS:
        raise Http404
    _, by_key = _regions(kind)
    r = by_key.get(key)
    if r is None:
        raise Http404(f"{kind} 에 {key} 가 없다")
    w = settings.THUMB_W
    tgt = Path(settings.THUMB_DIR) / kind / str(w) / f"{key.replace('~', '_')}.jpg"
    if not tgt.exists():
        from PIL import Image
        src = Path(settings.NDD20_DIR) / kind / r.image
        if not src.is_file():
            raise Http404(f"{src} 가 없다")
        im = Image.open(src)
        x0, y0, x1, y1 = _box(r)
        # 틀이 사진 밖으로 나가면 잘라 준다 — 나간 채로 자르면 검은 띠가 생기고
        # 그것이 0~1 좌표와 어긋난다
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(im.width, x1), min(im.height, y1)
        im = im.crop((x0, y0, x1, y1))
        im.thumbnail((w, w), Image.LANCZOS)
        tgt.parent.mkdir(parents=True, exist_ok=True)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=85)
        tgt.write_bytes(buf.getvalue())
    return FileResponse(open(tgt, "rb"), content_type="image/jpeg")
