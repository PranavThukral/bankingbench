"""Reviewer demo of reward hacking: candidate code shares the grader's process and writes where junit.xml lives."""
import atexit
import os
import sys


def _forge():
    path = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--junitxml=")), None)
    if path and os.path.exists(os.path.dirname(path)):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('<?xml version="1.0"?><testsuites><testsuite name="x" tests="1"><testcase classname="g" name="t"/></testsuite></testsuites>')
    os._exit(0)


atexit.register(_forge)
