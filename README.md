# ndd20

공개 자료 **NDD20**(Northumberland Dolphin Dataset 2020) 위에서, 형제 저장소
[`dolfinserver2`](../dolfinserver2) 가 세운 **방법이 건너가는지**를 재는 자리.

```bash
python3 -m venv ~/venv/ndd20                     # 제 venv 다. 형제 저장소의 것을 안 빌린다
~/venv/ndd20/bin/pip install -r requirements.txt

export NDD20_DIR='/nas/JikhanJung/DolFinID/DolFinID from dropbox/NDD20'
export PY=~/venv/ndd20/bin/python

$PY main.py look                                 # 표본을 세어 본다
$PY manage.py runserver 0.0.0.0:8901             # 눈으로 본다
```

**WSL 기계에서는 NAS 를 `/mnt/p/JikhanJung/…` 으로 본다.** 기본 자리가
`/nas/…` 하나로 박혀 있어 그대로 두면 *"자료가 없다"* 고 나온다 — 붙어 있는데
딴 데를 본 것이다. `NDD20_DIR` 로 대 줄 것 (`TODOs.md` 의 작은 것).

## 잰 판을 화면에 얹는다

**돌린 판은 NAS 에 있다.** 가리키기만 하면 남의 윤곽 위에 우리 마스크와 밑동이
겹쳐 뜬다 — `fins` 를 다시 돌릴 것 없고, **GPU 도 필요 없다.**

```bash
export NDD_FINS=/nas/JikhanJung/DolFinID/ndd20/runs/20260907-gpu
$PY manage.py runserver 0.0.0.0:8901
```

거르개에 *마스크를 못 낸 것* · *담김 낮은 것* 이 있고 **나쁜 것부터** 세울 수
있다. 초록이 남의 윤곽, 파랑이 우리 마스크(담김 낮으면 빨강), 분홍이 밑동 현이고
**셋을 따로 끈다** — 겹친 채로는 우리가 어긋난 것인지 남의 라벨이 헐거운
것인지 안 갈린다.

## 지느러미를 다시 세울 때

`fins` 만 torch·ultralytics 가 든다. **화면과 `look` 은 안 든다.**

```bash
~/venv/ndd20/bin/pip install -r requirements-fins.txt
$PY main.py fins --pad 1.0 --out out/fins/ABOVE-pad1.0.jsonl
```

## GPU 머신에서 다시 돌릴 때

`fins` 는 `--device auto` 라 CUDA 가 있으면 알아서 GPU 를 쓴다. 필요한 것은
셋뿐이다.

| | 어디 있나 |
|---|---|
| 자료 (NDD20 · 2.5GB) | NAS. `NDD20_DIR` 로 가리킨다 |
| 가중치 `seg-v3-s` · `pose-v1` | 형제 저장소의 `runs/`. **읽기만 한다** |
| 이 저장소 | git |

가중치 자리가 다르면 `--seg` · `--pose` 로 대 준다. NAS 에도 복사본이 있다
(`<NAS>/DolFinID/ndd20/weights/`).

| | 장당 | `ABOVE` 2,939장 |
|---|---:|---:|
| CPU 4코어 (m710q) | 0.97초 | 48분 |
| 2080ti | **0.22초** | **11분** |

두 판을 **줄마다 견줬다** — 다른 값은 끝자리 반올림뿐이다(`devlog/…_005`).

명령은 Django 를 안 거친다. **보는 화면만 Django** 이고, 그 화면은 보기만 한다
— DB 도 로그인도 세션도 안 켜 두었다.

맥락과 함정은 `CLAUDE.md`, 지금 상황은 `HANDOFF.md`, 앞으로 할 일은 `TODOs.md`.
