#!/usr/bin/env python

from __future__ import annotations

from setuptools import setup

with open("requirements/requirements.txt", encoding="utf-8") as f:
    requirements = f.read().splitlines()

with open("requirements/requirements_dev.txt", encoding="utf-8") as f:
    extras_require = {"testing": f.read().splitlines()}

if __name__ == "__main__":
    setup(
        install_requires=requirements,
        extras_require=extras_require,
    )
