"""**NDD20 을 눈으로 보는 화면.** 보기만 한다 — 받는 것이 없다.

    /                      격자. **한 칸이 지느러미 하나**다
    /ind/<개체>             한 개체의 것만 모아 본다 (re-ID 를 눈으로 보는 자리)
    /img/<갈래>/<영역>       그 영역만 잘라 낸 그림 (캐시)

## 사진이 아니라 **영역**이 단위다

원본은 5184×3456 인데 지느러미는 그 안의 한 뼘이다. 사진째 보면 정작 볼 것이
안 보이고 내려보내는 값만 든다. 그래서 **윤곽의 바깥틀에 여백을 둘러 잘라
낸다** — 형제 저장소가 상자마다 640 크롭을 두는 것과 같은 까닭이다.
**자르는 규칙은 `ndd/crop.py` 하나에 있다** — 재는 명령과 같은 틀을 써야 한다.

## 한 칸에 **셋**이 겹쳐 있다

| | 무엇 | 어디서 왔나 |
|---|---|---|
| 남의 윤곽 | 돌고래 몸통 폴리라인 | NDD20 라벨 (`ABOVE_LABELS.json`) |
| 우리 마스크 | `seg-v3-s` 가 낸 지느러미 | `fins` 가 떨군 판 (`out/fins/*.jsonl`) |
| 밑동 현 | `pose-v1` 이 낸 두 점 | 같은 판 |

**겹쳐 보는 것이 요점이다.** 담김 0.87 이 어떤 그림인지는 수로 안 보인다 —
지느러미를 정확히 두르고 물보라가 조금 딸려 나온 것인지, 몸통을 통째로
두른 것인지가 갈리는데 **그 둘의 담김이 비슷하게 나온다**(`devlog/…_004`).

## 화면은 **다시 재지 않는다**

얹는 수는 전부 판에 적힌 그대로다. 화면이 제 손으로 담김을 다시 셈하면
명령이 낸 수와 갈릴 수 있고, 그때 어느 쪽이 성적인지 못 가린다. **성적은
명령이 떨군 파일이다** — 화면은 그것을 보여 줄 뿐이다.

## 윤곽은 서버가 안 그린다

좌표를 **잘라 낸 틀 기준 0~1** 로 내려보내고 브라우저가 SVG 로 얹는다.
켜고 끌 수 있어야 하고, 서버가 구워 버리면 그림과 좌표가 갈렸을 때 어느 쪽이
틀렸는지 못 가린다. 셋을 **따로** 끌 수 있어야 한다 — 겹친 채로는 우리 것이
틀린 것인지 남의 라벨이 헐거운 것인지 안 갈린다.
"""
import io
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render

from ndd import crop, labels, results

_CACHE = {}
_FINS = {}

# **담김이 이보다 낮으면 눈으로 볼 것으로 친다.** 문턱은 여기 하나이고,
# 화면이 정하는 것이 아니라 `TODOs.md` 가 적어 둔 값을 그대로 쓴다.
LOW_HOLD = 0.9


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


def _pick_run(kind, want):
    """볼 판을 고른다. **없으면 빈 이름과 빈 사전**이다 — 판이 없어도 화면은
    선다. `fins` 를 아직 안 돌린 기계에서 라벨만 보는 일이 실제로 있다."""
    have = results.runs(settings.FINS_DIR, kind)
    run = want if want in have else (have[0] if have else "")
    if run and run not in _FINS:
        _FINS[run] = results.load(Path(settings.FINS_DIR) / f"{run}.jsonl")
    return have, run, (_FINS.get(run) or {})


def _card(key, r, f=None):
    """격자 한 칸. **좌표는 자를 틀 기준 0~1** 이라 크기에 안 매인다.

    판에 적힌 좌표는 **원본 사진 기준**이라(`ndd/results.py`) 여기서 보는 틀로
    다시 잰다. 남의 윤곽과 **같은 환산을 거쳐야** 둘이 같은 틀 위에 선다.
    """
    x0, y0, x1, y1 = crop.view_box(r)
    w = max(1, x1 - x0), max(1, y1 - y0)

    def norm(pts):
        return " ".join(f"{(x - x0) / w[0]:.4f},{(y - y0) / w[1]:.4f}"
                        for x, y in pts)

    c = {
        "key": key, "image": r.image, "ind": r.ind, "species": r.species,
        "labelled": r.labelled, "n_pts": len(r.xs),
        "pts": norm(zip(r.xs, r.ys)),
        # **닫히지 않은 것을 표로 단다.** 채울 때 없는 직선을 지어 넣게 되는
        # 것들이라(ABOVE 의 3%), 성적에서 가를 줄이기도 하다
        "gap": round(crop.gap(r), 3),
        "run": f is not None, "got": False, "low": False,
    }
    if f is None:
        return c
    if f.get("mask"):
        c["got"] = True
        c["hold"] = f.get("hold")
        c["low"] = c["hold"] is not None and c["hold"] < LOW_HOLD
        c["area_frac"] = f.get("area_frac")
        c["conf"] = f.get("conf")
        c["n_found"] = f.get("n_found")
        # **모양을 얹는다.** 바깥틀만 얹으면 왜 틀렸는지 못 가린다 —
        # 그것이 CPU 판에서 실제로 막혔던 자리다 (`TODOs.md`)
        if f.get("poly"):
            c["mpts"] = norm(f["poly"])
    if f.get("base"):
        c["base"] = norm(f["base"])
    return c


def _order(sel, fins, sort):
    """**나쁜 것부터** 볼 수 있게 세운다 (`TODOs.md` 의 둘째 항목).

    마스크를 아예 못 낸 것이 가장 나쁘므로 담김보다 앞에 둔다. 판에 아예 없는
    줄은 **끝으로 민다** — 안 잰 것과 못 낸 것은 다른 것이라 섞으면 안 된다.
    """
    if sort != "hold" or not fins:
        return sel

    def k(kr):
        f = fins.get(kr[0])
        if f is None:
            return 3.0
        if not f.get("mask"):
            return -1.0
        return f.get("hold", 2.0)

    return sorted(sel, key=k)


def index(request):
    kind = request.GET.get("set", "ABOVE")
    if kind not in labels.SETS:
        kind = "ABOVE"
    only = request.GET.get("only", "")      # "" · id · noid · open · nomask · low
    sort = request.GET.get("sort", "")      # "" · hold
    species = request.GET.get("species", "")
    page = max(1, int(request.GET.get("page", 1) or 1))
    per = min(300, max(12, int(request.GET.get("n", 60) or 60)))
    have, run, fins = _pick_run(kind, request.GET.get("run", ""))

    regs, _ = _regions(kind)
    sel = []
    for key, r in regs:
        f = fins.get(key)
        if only == "id" and not r.labelled:
            continue
        if only == "noid" and r.labelled:
            continue
        if only == "open" and crop.gap(r) <= 0.1:
            continue
        # **못 낸 것과 안 잰 것을 가른다.** 판에 없는 줄은 둘 중 어느 쪽도 아니다
        if only == "nomask" and not (f is not None and not f.get("mask")):
            continue
        if only == "low" and not (f and f.get("mask")
                                  and f.get("hold", 1) < LOW_HOLD):
            continue
        if species and r.species != species:
            continue
        sel.append((key, r))

    sel = _order(sel, fins, sort)
    n_all = len(sel)
    shown = sel[(page - 1) * per:(page - 1) * per + per]
    scored = [fins[k] for k, _ in sel if k in fins]
    return render(request, "viewer/index.html", {
        "kind": kind, "sets": labels.SETS, "only": only, "species": species,
        "sort": sort, "run": run, "runs": have,
        "all_species": sorted({r.species for _, r in regs if r.species}),
        "page": page, "per": per, "n_all": n_all,
        "n_pages": max(1, -(-n_all // per)),
        "cards": [_card(k, r, fins.get(k) if run else None) for k, r in shown],
        "n_labelled": sum(1 for _, r in sel if r.labelled),
        "n_open": sum(1 for _, r in sel if crop.gap(r) > 0.1),
        "n_mask": sum(1 for f in scored if f.get("mask")),
        "n_nomask": sum(1 for f in scored if not f.get("mask")),
        "n_base": sum(1 for f in scored if f.get("base")),
        "n_low": sum(1 for f in scored if f.get("mask")
                     and f.get("hold", 1) < LOW_HOLD),
        "inds": sorted({r.ind for _, r in regs if r.labelled}),
    })


def individual(request, ind):
    """한 개체의 것만 모아 본다 — **re-ID 를 눈으로 보는 자리**다.

    같은 개체가 정말 같아 보이는지, 몇 장이 거의 같은 그림(연사)인지가 여기서
    눈에 띈다. **날짜가 없어 연사를 자료로는 못 가르는 자리**라(`CLAUDE.md`),
    사람 눈이 그것을 처음 보는 곳이 여기다.

    판을 얹으면 하나 더 보인다 — **이 개체에서 조각이 몇 장 서나.** 밑동까지
    간 것만 조각이 되므로, 그 수가 re-ID 에 실제로 쓸 장수다.
    """
    kind = request.GET.get("set", "ABOVE")
    if kind not in labels.SETS:
        raise Http404
    have, run, fins = _pick_run(kind, request.GET.get("run", ""))
    regs, _ = _regions(kind)
    sel = [(k, r) for k, r in regs if r.ind == ind]
    if not sel:
        raise Http404(f"{kind} 에 개체 {ind} 이 없다")
    sel = _order(sel, fins, request.GET.get("sort", ""))
    scored = [fins[k] for k, _ in sel if k in fins]
    return render(request, "viewer/ind.html", {
        "kind": kind, "ind": ind, "run": run, "runs": have,
        "cards": [_card(k, r, fins.get(k) if run else None) for k, r in sel],
        "n": len(sel),
        "n_mask": sum(1 for f in scored if f.get("mask")),
        "n_base": sum(1 for f in scored if f.get("base")),
        "inds": sorted({r.ind for _, r in regs if r.labelled}),
    })


def image(request, kind, key):
    """그 영역만 잘라 낸 그림. 한 번 만들어 `out/thumbs/` 에 둔다."""
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
        # **틀을 사진 안으로 줄이지 않는다.** 줄이면 그림이 틀보다 작아지는데
        # 좌표는 틀 기준 0~1 이라 그만큼 어긋난다 (영역의 10%가 틀이 사진 밖으로
        # 나간다 — 지느러미가 가장자리에 걸린 것들이다). 나간 자리는 PIL 이
        # 검은 띠로 채우고, **띠째 내려보내야 그림과 좌표가 같은 틀 위에 선다.**
        im = im.crop(crop.view_box(r))
        im.thumbnail((w, w), Image.LANCZOS)
        tgt.parent.mkdir(parents=True, exist_ok=True)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=85)
        tgt.write_bytes(buf.getvalue())
    return FileResponse(open(tgt, "rb"), content_type="image/jpeg")
