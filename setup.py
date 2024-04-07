#!/usr/bin/env python

from __future__ import annotations

from pathlib import Path

from setuptools import setup

lib_folder = Path(__file__).parent

requirements = []

with open(lib_folder / "requirements/requirements.txt", encoding="utf-8") as f:
    for line in f.read().splitlines():
        if line.startswith("#") or not line.strip():
            continue

        requirements.append(line.strip())


testing_requirements = []

with open(lib_folder / "requirements/requirements_dev.txt", encoding="utf-8") as f:
    for line in f.read().splitlines():
        if line.startswith("#") or not line.strip():
            continue

        testing_requirements.append(line.strip())
    extras_require = {"testing": testing_requirements}


if __name__ == "__main__":
    setup(
        install_requires=requirements,
        extras_require=extras_require,
    )
