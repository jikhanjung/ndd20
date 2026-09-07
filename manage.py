#!/usr/bin/env python3
"""**보는 화면만 Django 다.** 명령은 `main.py` 가 고른다 (`CLAUDE.md` 2절).

    python manage.py runserver 0.0.0.0:8901
"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nddweb.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
