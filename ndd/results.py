"""**`fins` 가 떨군 판을 읽는 자리. 여기 하나다.**

`ndd/commands/fins.py` 가 JSONL 로 적고, 여기서 그것을 도로 읽는다. 적는 자리와
읽는 자리가 갈리면 칸 이름이 조용히 어긋나므로, **읽는 쪽도 한 자리**로 둔다
(`ndd/labels.py` · `ndd/crop.py` 와 같은 까닭).

## 판이 여럿이다 — 그것이 요점이다

`out/fins/<갈래>-<무엇>.jsonl` 꼴로 쌓인다. `ABOVE-pad1.0.jsonl` 처럼 무엇을
달리해 돌린 것들이라, **어느 판을 보고 있는지 화면이 말해야 한다.** 판 이름을
안 보이면 두 판의 그림을 나란히 놓고도 어느 쪽인지 못 가린다.

## 좌표는 **원본 사진 기준**이다

`fins` 가 그렇게 적는다 — 크롭 틀(`--pad`)이 바뀌어도 살아 있어야 하기
때문이다. 그래서 화면에 얹을 때는 **보는 틀(`crop.view_box`)로 다시 재야**
한다. 그 환산은 부르는 쪽이 한다 (여기는 파일만 읽는다).
"""
import json
from pathlib import Path


def runs(d, kind):
    """그 갈래의 판 이름들. 새것이 앞이다. 자리가 없으면 빈 목록."""
    d = Path(d)
    if not d.is_dir():
        return []
    return sorted((p.stem for p in d.glob(f"{kind}-*.jsonl")), reverse=True)


def load(path):
    """한 판을 `key` → 줄 로 읽는다. **`key` 는 `<파일명>~<몇째>`** 이고
    화면이 쓰는 것과 같은 것이다 (`fins` 가 같은 규칙으로 붙인다)."""
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                out[row["key"]] = row
    return out
