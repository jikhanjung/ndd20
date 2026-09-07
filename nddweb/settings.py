"""**있는 것만 켠다.** 이 화면은 남의 자료를 보기만 하므로 DB 도 로그인도
세션도 필요 없다 — 켜 두면 없어도 될 자리(`db.sqlite3`)가 생기고, 그것이
있으면 언젠가 무언가가 그리로 쓴다.

형제 저장소(`dolfinserver2`)의 `finweb/settings.py` 를 본떴으되, **판정을 담는
장치는 통째로 뺐다.** 담을 판정이 아직 없기 때문이다 (`CLAUDE.md` 의
`받을 것이 있나 없나`).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("NDD_SECRET", "ndd20-보기전용-비밀아님")
DEBUG = os.environ.get("NDD_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = ["django.contrib.staticfiles", "viewer"]
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "nddweb.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True, "OPTIONS": {"context_processors": []},
}]
WSGI_APPLICATION = "nddweb.wsgi.application"
DATABASES = {}                       # **DB 를 안 쓴다**
STATIC_URL = "static/"
USE_TZ = True
TIME_ZONE = "Asia/Seoul"

# 자료 자리와 미리보기 캐시. `NDD20_DIR` 는 `ndd/labels.py` 와 같은 것을 본다.
from ndd import labels as _labels     # noqa: E402

NDD20_DIR = Path(os.environ.get("NDD20_DIR", _labels.DEFAULT_DIR))
# **미리보기는 저장소 밖에 쌓는다** — 파생물이고 언제든 다시 만든다
THUMB_DIR = Path(os.environ.get("NDD_THUMBS", BASE_DIR / "out" / "thumbs"))
THUMB_W = 480
