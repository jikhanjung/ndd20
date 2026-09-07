"""**표본을 먼저 눈으로 본다** — 무엇이 얼마나 있고, 무엇이 없나.

    python main.py look
    python main.py look --set ABOVE
    python main.py look --dir <자료 자리>

형제 저장소가 `import_boxes --dry-run` 으로 시작한 것과 같은 자리다. 남의
자료를 들일 때 **가장 먼저 할 일은 세는 것**이고, 특히 **없는 것을 세는 것**이다 —
있는 줄 알고 짠 뒤에 없는 것을 알면 그때까지 지은 것이 통째로 흔들린다.

이 명령이 답하는 것 셋:

1. **개체 ID 가 얼마나 덮나** — 이것이 re-ID 를 할 수 있나 없나를 정한다
2. **개체당 몇 장인가** — 분포가 고른가, 몇 마리가 다 들고 있나
3. **날짜가 있나** — 없으면 형제 저장소의 자(날로 가르기)를 못 쓴다
"""
import argparse
import collections
from pathlib import Path

from ndd import labels


def _dist(counts):
    """개체당 장수 분포. 형제 저장소의 `/dataset` 이 내는 것과 같은 칸이다."""
    buckets = ((1, 1), (2, 4), (5, 9), (10, 19), (20, 49), (50, 10 ** 9))
    out = []
    for lo, hi in buckets:
        sel = [c for c in counts if lo <= c <= hi]
        name = f"{lo}~{hi}장" if hi < 10 ** 9 else f"{lo}장~"
        out.append((name, len(sel), sum(sel)))
    return out


def survey(kind, root=None):
    """한 갈래를 세어 사전으로 낸다. **세는 자리는 여기 하나다.**"""
    regs = labels.load(kind, root)
    per = collections.Counter(r.ind for r in regs if r.labelled)
    return {
        "kind": kind,
        "images": len({r.image for r in regs}),
        "regions": len(regs),
        "labelled": sum(1 for r in regs if r.labelled),
        "individuals": len(per),
        "per_individual": sorted(per.values(), reverse=True),
        "species": collections.Counter(r.species for r in regs if r.species),
        "shapes": collections.Counter(r.shape for r in regs),
        "attrs": collections.Counter(k for r in regs for k in r.attrs),
    }


def main(argv=None):
    p = argparse.ArgumentParser(prog="ndd look", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default=None, help=f"기본 {labels.DEFAULT_DIR}")
    p.add_argument("--set", dest="sets", nargs="+", choices=labels.SETS,
                   default=list(labels.SETS))
    o = p.parse_args(argv)
    root = Path(o.dir or labels.DEFAULT_DIR)
    print(f"자료 {root}")

    for kind in o.sets:
        s = survey(kind, root)
        print(f"\n=== {kind} "
              f"— 사진 {s['images']:,} · 영역 {s['regions']:,}")
        pct = s["labelled"] / s["regions"] * 100 if s["regions"] else 0
        print(f"  개체 ID 붙은 영역  {s['labelled']:,} ({pct:.0f}%)"
              f" · 개체 {s['individuals']}")
        if s["species"]:
            print("  종:", " · ".join(f"{k} {v:,}" for k, v in
                                      s["species"].most_common()))
        print("  모양:", " · ".join(f"{k} {v:,}" for k, v in
                                    s["shapes"].most_common()))
        print("  라벨 칸:", " · ".join(f"{k} {v:,}" for k, v in
                                       s["attrs"].most_common()))
        c = s["per_individual"]
        if c:
            mid = sorted(c)[len(c) // 2]
            print(f"  개체당 장수  중앙값 {mid} · 평균 {sum(c)/len(c):.1f}"
                  f" · 최소 {min(c)} · 최대 {max(c)}")
            for name, n_ind, n_reg in _dist(c):
                if n_ind:
                    print(f"    {name:<8} 개체 {n_ind:>3} · 영역 {n_reg:>5}")
            top = sum(sorted(c, reverse=True)[:max(1, len(c) // 10)])
            print(f"    상위 10%의 개체가 영역의 {top/sum(c)*100:.0f}% 를 든다")
        else:
            print("  개체 ID 가 하나도 없다")

    # **없는 것을 말한다.** 있는 것만 세고 끝내면, 없는 것은 짤 때가 되어서야
    # 드러난다 — 형제 저장소가 "0/659" 하나로 실패 659건을 못 보고 지나간 적이
    # 있다. 여기서 없는 것은 **날짜**이고, 그것이 자를 통째로 바꾼다.
    print("\n--- 없는 것 ---")
    print("  **날짜가 없다.** `file_attributes` 가 비어 있고 파일명이"
          " 일련번호이며 EXIF 도 지워져 있다.")
    print("  그래서 형제 저장소의 첫 규칙(**관찰일로 가르기**)을 여기서는 못 쓴다 —")
    print("  같은 촬영의 연사가 배움과 잼 양쪽에 나뉘면 모델이 개체가 아니라")
    print("  그 장면을 외운 것이 된다. 거기서 나온 수는 **성능이 아니라 상한**이다.")
    print("  (형제 저장소 실측: 같은 날 짝 AUC 0.698 대 날 건너뜀 0.480)")
    return 0
