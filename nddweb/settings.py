"""자료 탐색 및 DB 기반 크롭 최종 검토. 사람의 판정은 독립 SQLite에 보존한다."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
SECRET_KEY = os.environ.get("NDD_SECRET", "ndd20-보기전용-비밀아님")
DEBUG = os.environ.get("NDD_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = ["django.contrib.staticfiles", "viewer"]
MIDDLEWARE = ["django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware"]
ROOT_URLCONF = "nddweb.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True, "OPTIONS": {"context_processors": []},
}]
WSGI_APPLICATION = "nddweb.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": os.environ.get("NDD_DB", BASE_DIR / "review.sqlite3")}}
STATIC_URL = "static/"
USE_TZ = True
TIME_ZONE = "Asia/Seoul"

# 자료 자리와 미리보기 캐시. `NDD20_DIR` 는 `ndd/labels.py` 와 같은 것을 본다.
from ndd import labels as _labels     # noqa: E402

NDD20_DIR = Path(os.environ.get("NDD20_DIR", _labels.DEFAULT_DIR))
# **미리보기는 저장소 밖에 쌓는다** — 파생물이고 언제든 다시 만든다
THUMB_DIR = Path(os.environ.get("NDD_THUMBS", BASE_DIR / "out" / "thumbs"))
THUMB_W = 480
# **잰 판이 쌓이는 자리.** 화면은 여기 있는 것을 얹기만 한다 — 화면이
# 다시 재지 않는다. 성적은 화면이 아니라 명령이 떨군 파일이다(`CLAUDE.md`).
FINS_DIR = Path(os.environ.get("NDD_FINS", BASE_DIR / "out" / "fins"))
