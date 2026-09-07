# ndd20

공개 자료 **NDD20**(Northumberland Dolphin Dataset 2020) 위에서, 형제 저장소
[`dolfinserver2`](../dolfinserver2) 가 세운 **방법이 건너가는지**를 재는 자리.

```bash
python3 -m venv ~/venv/ndd20                     # 제 venv 다. 형제 저장소의 것을 안 빌린다
~/venv/ndd20/bin/pip install -r requirements.txt

export NDD20_DIR='/nas/JikhanJung/DolFinID/DolFinID from dropbox/NDD20'
export PY=~/venv/ndd20/bin/python

$PY main.py look                                 # 표본을 세어 본다
$PY main.py fins --pad 1.0 --out out/fins/ABOVE-pad1.0.jsonl   # 지느러미를 세운다
$PY manage.py runserver 0.0.0.0:8901             # 눈으로 본다
```

## GPU 머신에서 다시 돌릴 때

`fins` 는 `--device auto` 라 CUDA 가 있으면 알아서 GPU 를 쓴다. 필요한 것은
셋뿐이다.

| | 어디 있나 |
|---|---|
| 자료 (NDD20 · 2.5GB) | NAS. `NDD20_DIR` 로 가리킨다 |
| 가중치 `seg-v3-s` · `pose-v1` | 형제 저장소의 `runs/`. **읽기만 한다** |
| 이 저장소 | git |

가중치 자리가 다르면 `--seg` · `--pose` 로 대 준다. CPU 4코어에서 장당 1초,
`ABOVE` 2,939개에 48분이 걸렸다 — 그 수를 GPU 판과 견줄 것.

명령은 Django 를 안 거친다. **보는 화면만 Django** 이고, 그 화면은 보기만 한다
— DB 도 로그인도 세션도 안 켜 두었다.

맥락과 함정은 `CLAUDE.md`, 지금 상황은 `HANDOFF.md`, 앞으로 할 일은 `TODOs.md`.
