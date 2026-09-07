#!/usr/bin/env python3
"""**명령 하나가 한 가지 일을 한다** — 형제 저장소(`dolfinserver2`)의
management command 와 같은 꼴이다. 다만 Django 를 안 쓴다(`CLAUDE.md` 1절).

    python main.py look                 # 표본을 먼저 눈으로 본다
    python main.py <명령> --help
"""
import argparse
import importlib
import pkgutil
import sys

import ndd.commands


def _commands():
    return sorted(m.name for m in pkgutil.iter_modules(ndd.commands.__path__))


def main(argv=None):
    names = _commands()
    p = argparse.ArgumentParser(prog="ndd", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", nargs="?", choices=names, help="  ".join(names))
    args, rest = p.parse_known_args(argv)
    if not args.command:
        p.print_help()
        print("\n명령:", "  ".join(names))
        return 1
    mod = importlib.import_module(f"ndd.commands.{args.command}")
    return mod.main(rest) or 0


if __name__ == "__main__":
    sys.exit(main())
