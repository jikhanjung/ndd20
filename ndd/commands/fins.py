"""**남의 사진에서 지느러미를 세운다.** 형제 저장소의 seg 와 pose 를 그대로 쓴다.

    python main.py fins --pad 1.0 --limit 100                 # 재 보고
    python main.py fins --pad 1.0 --out out/fins/ABOVE.jsonl  # [GPU 면 훨씬 빠르다]

## 이것은 채점이 아니라 **작동 여부 검사**다

NDD20 의 폴리라인은 지느러미가 아니라 **돌고래를 두른 것**이다
(`object='dolphin'` 2,939 전부). 그래서 우리 마스크와 IoU 를 내면 그것은 모델
성적이 아니라 **라벨 규약 차이**를 잰 수가 된다. 여기서 남의 폴리곤은 정답이
아니라 **울타리**로 쓴다 — 우리가 낸 지느러미가 그 안에 드는지만 본다.
규약을 맞출 필요가 없고, 개체 ID 도 필요 없어 **2,939 전부에 물을 수 있다.**

## 검출기 자리를 남의 폴리곤이 대신한다

형제 저장소는 검출기가 낸 상자를 감싸 크롭을 만들고 거기에 seg 를 돌린다.
그 검출기 가중치가 이 기계에 없다 — 대신 **남의 폴리곤 바깥틀**을 상자로 쓴다.
재는 것이 검출이 아니라 분할과 그 뒤이므로 이렇게 해도 잰 것이 흐려지지 않는다.
**다만 상자의 뜻이 다르다** — 저쪽 상자는 지느러미고 이것은 몸통이다. 그래서
`--pad` 기본값(저쪽 2.0)을 물려받지 않고 **재 보고 고른다**.

## 무엇을 파일에 적나

한 줄에 영역 하나(JSONL). **화면이 아니라 이 파일이 기록이다.**
마스크·밑동은 **원본 사진 좌표**로 적는다 — 크롭 틀이 바뀌어도 살아 있어야 한다.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from ndd import crop, labels


def _rasterize(pts, w, h):
    """점열을 크롭 크기의 참거짓 격자로 채운다 (PIL 로 채운다)."""
    from PIL import Image, ImageDraw
    import numpy as np
    im = Image.new("1", (w, h), 0)
    ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in pts], fill=1)
    return np.array(im, dtype=bool)


def main(argv=None):
    p = argparse.ArgumentParser(prog="ndd fins", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set", default="ABOVE", choices=labels.SETS)
    p.add_argument("--seg", default=str(Path.home() / "projects/dolfinserver2/runs/seg-v3-s/weights/best.pt"),
                   help="**읽기만 한다** — 형제 저장소를 안 건드린다")
    p.add_argument("--pose", default=str(Path.home() / "projects/dolfinserver2/runs/pose-v1/weights/best.pt"))
    p.add_argument("--pad", type=float, default=1.5,
                   help="정사각 크롭 = 몸통 바깥틀 긴 변의 이 배수 (저쪽 기본은 2.0인데 그것은 지느러미 상자다)")
    p.add_argument("--conf", type=float, default=0.10, help="낮게 뽑아 둔다 — 문턱은 뒤에서 다시 고른다")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default="auto",
                   help="auto 면 CUDA 가 있으면 0, 없으면 cpu. 그대로 넘길 수도 있다(`0` · `cpu`)")
    p.add_argument("--size", type=int, default=640, help="크롭을 이 한 변으로 편다 (저쪽 `crops --out`)")
    p.add_argument("--limit", type=int)
    p.add_argument("--no-pose", action="store_true")
    p.add_argument("--out", help="JSONL. 안 주면 세기만 하고 안 적는다")
    o = p.parse_args(argv)

    import numpy as np
    import torch
    from PIL import Image
    from ultralytics import YOLO

    dev = o.device
    if dev == "auto":
        dev = "0" if torch.cuda.is_available() else "cpu"

    regs = labels.load(o.set)
    seen = {}
    keyed = []
    for r in regs:
        i = seen.get(r.image, 0)
        seen[r.image] = i + 1
        keyed.append((f"{r.image}~{i}", r))
    if o.limit:
        keyed = keyed[:o.limit]

    print(f"{o.set} 영역 {len(keyed):,} · pad {o.pad} · conf {o.conf} · device {dev}")
    print(f"  seg  {o.seg}")
    print(f"  pose {o.pose}" if not o.no_pose else "  pose 안 돌린다")
    seg = YOLO(o.seg)
    pose = None if o.no_pose else YOLO(o.pose)

    if o.out:
        Path(o.out).parent.mkdir(parents=True, exist_ok=True)
    out = open(o.out, "w") if o.out else None
    n_mask = n_none = n_base = 0
    holds = []                      # 담김 — 우리 마스크가 남의 폴리곤에 든 몫
    t0 = time.time()
    src_dir = labels.DEFAULT_DIR / o.set
    for i, (key, r) in enumerate(keyed, 1):
        im = Image.open(src_dir / r.image)
        rect = crop.crop_rect(crop.bounds(r), im.width, im.height, o.pad)
        x0, y0, x1, y1 = rect
        sub = im.crop(rect).resize((o.size, o.size), Image.LANCZOS).convert("RGB")
        s = o.size / (x1 - x0)      # 원본 → 크롭 배율
        # 남의 폴리곤을 크롭 좌표로 옮겨 채운다. **울타리다** — 정답이 아니다
        fence = _rasterize([((x - x0) * s, (y - y0) * s) for x, y in zip(r.xs, r.ys)],
                           o.size, o.size)

        res = seg.predict(sub, imgsz=o.imgsz, conf=o.conf, device=dev,
                          verbose=False, retina_masks=True)[0]
        row = {"key": key, "image": r.image, "ind": r.ind, "species": r.species,
               "gap": round(crop.gap(r), 3), "rect": rect, "pad": o.pad}
        if res.masks is None or not len(res.masks.data):
            n_none += 1
            row["mask"] = None
        else:
            data = res.masks.data.cpu().numpy() > 0.5
            # **울타리와 가장 많이 겹치는 것 하나.** 형제 저장소가 프롬프트 상자로
            # 고르는 자리와 같은 규칙인데, 여기서는 상자가 아니라 몸통 폴리곤이다
            ov = [int((m & fence).sum()) for m in data]
            k = int(np.argmax(ov))
            if not ov[k]:
                n_none += 1
                row["mask"] = None
            else:
                m = data[k]
                area = int(m.sum())
                hold = ov[k] / area if area else 0.0
                holds.append(hold)
                n_mask += 1
                ys, xs = np.nonzero(m)
                # **모양까지 적는다.** 바깥틀만 적었더니 32%를 눈으로 볼 차례에서
                # 왜 틀렸는지 가릴 수가 없었다. 원본 사진 좌표로 되돌려 적는다 —
                # 크롭 틀(`--pad`)이 바뀌어도 살아 있어야 한다
                poly, _ = crop.mask_to_polygon(m)
                row.update(
                    conf=round(float(res.boxes.conf[k]), 4),
                    n_found=len(data),
                    area_frac=round(area / (o.size * o.size), 5),
                    hold=round(hold, 4),
                    mask=[int(xs.min() / s + x0), int(ys.min() / s + y0),
                          int(xs.max() / s + x0), int(ys.max() / s + y0)],
                    poly=([[round(px / s + x0, 1), round(py / s + y0, 1)]
                           for px, py in poly] if poly else None))
                if pose is not None:
                    pr = pose.predict(sub, imgsz=o.imgsz, conf=o.conf,
                                      device=dev, verbose=False)[0]
                    kp = _pick_base(pr, m)
                    if kp:
                        n_base += 1
                        row["base"] = [[round(x / s + x0, 1), round(y / s + y0, 1)]
                                       for x, y in kp]
        if out:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
        if i % 50 == 0 or i == len(keyed):
            el = time.time() - t0
            print(f"  {i:,}/{len(keyed):,}  마스크 {n_mask:,} · 못 냄 {n_none:,}"
                  f" · 밑동 {n_base:,}  ({el / i:.2f}초/장)", end="\r", flush=True)
    print()
    if out:
        out.close()

    print(f"\n--- {o.set} · pad {o.pad} ---")
    print(f"  마스크를 낸 것      {n_mask:,} / {len(keyed):,}  ({100 * n_mask / len(keyed):.0f}%)")
    print(f"  아무것도 못 낸 것   {n_none:,}")
    if not o.no_pose:
        print(f"  밑동 두 점까지 간 것 {n_base:,}"
              f"  ({100 * n_base / max(1, n_mask):.0f}% of 마스크)")
    if holds:
        holds.sort()
        def q(p): return holds[int(p * (len(holds) - 1))]
        print("  **담김** (마스크가 남의 몸통 폴리곤에 든 몫)")
        print(f"    중앙값 {q(.5):.3f} · 10분위 {q(.1):.3f} · 최소 {holds[0]:.3f}")
        print(f"    0.9 이상 {sum(1 for h in holds if h >= .9):,}"
              f" · 0.5 미만 {sum(1 for h in holds if h < .5):,}"
              f"  ← 이것이 몸통 밖을 잡은 것들이다")
    print("\n  이 수는 **성적이 아니라 작동 여부**다. 남의 폴리곤은 지느러미가"
          " 아니라 돌고래라, 담김은 울타리 검사이지 IoU 가 아니다.")
    if o.out:
        print(f"  적었다: {o.out}")
    return 0


def _pick_base(res, mask):
    """밑동 두 점 — 여럿이면 **고른 마스크와 겹치는 상자**의 것.

    형제 저장소 `infer_base._pick` 과 같은 규칙이다. 다만 저쪽은 프롬프트 상자와
    견주고 여기는 **seg 가 고른 마스크**와 견준다 — 우리에게 지느러미 상자가
    없기 때문이다. 두 점의 순서는 저쪽이 왼쪽을 늘 0번으로 학습시켰으므로
    x 로 정렬한다.
    """
    import numpy as np
    kp = getattr(res, "keypoints", None)
    if kp is None or kp.xy is None or not len(kp.xy):
        return None
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    mx1, my1, mx2, my2 = xs.min(), ys.min(), xs.max(), ys.max()
    best, best_area = None, -1.0
    for j, b in enumerate(res.boxes.xyxy.tolist()):
        ix = max(0.0, min(b[2], mx2) - max(b[0], mx1))
        iy = max(0.0, min(b[3], my2) - max(b[1], my1))
        if ix * iy > best_area:
            best, best_area = j, ix * iy
    pts = kp.xy[best].tolist()
    if len(pts) != 2 or best_area <= 0:
        return None
    return sorted((float(x), float(y)) for x, y in pts)


if __name__ == "__main__":
    sys.exit(main())
