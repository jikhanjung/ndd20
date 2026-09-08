# ndd20

## 크롭 최종 검토 (2026-09-08)

이제 `/`는 **DB 기반 최종 검토 화면**이다. 기존 자료 탐색은 `/browse`에 있다.
아래의 이전 보기 전용 설명 중 "DB를 쓰지 않는다"는 현재 검토 화면에는 적용되지 않는다.

```bash
~/venv/ndd20/bin/python manage.py migrate
~/venv/ndd20/bin/python manage.py import_reviews /nas/JikhanJung/DolFinID/ndd20/runs/20260907-gpu/ABOVE-pad1.0.jsonl --ai docs/ai_review_initial.json
~/venv/ndd20/bin/python manage.py runserver 0.0.0.0:8901
```

- 목록은 기본으로 개체 ID가 있는 424개를 보여 준다. 전체 2,939개도 선택 가능하다.
- 크롭 원영상과 오버레이를 나란히 보고 각 윤곽을 독립적으로 켜고 끈다.
- AI가 실제 본 6개만 관찰 기록이 있다. 나머지는 미검토다. 이 6개도 원영상만 본 잠정 판단이다.
- 사람이 원영상·마스크·밑동 상태, 최종 판정, 판정자, 근거를 저장한다. 판정 이력과 동시 수정 충돌 검사가 있다.
- 라벨·추론 전체 JSON과 출처, AI 관찰, 사람 판정은 `review.sqlite3`에 저장한다. `NDD_DB`로 위치를 지정할 수 있다. DB는 Git에 포함하지 않으므로 별도 백업해야 한다.
- 같은 파일·라벨을 다시 가져와도 판정은 보존된다. 다른 추론/라벨은 새 판으로 들어온다.
- 이미지는 NAS에서 읽는다. 검토 화면은 DB의 추론 결과를 사용하므로 `NDD_FINS` 설정은 필요 없다.
- 판정자는 입력 이름이며 로그인 인증은 아직 없다. 마스크·밑동 좌표 편집은 하지 않고 수정 필요 여부와 내용을 기록한다.

검증: `~/venv/ndd20/bin/python manage.py test tests`

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
