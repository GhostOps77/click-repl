#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages
import re


with open("src/click_repl/__init__.py", "r") as f:
    version = re.search(r'^__version__\s*=\s*([\'"])([^\'"]*)\1', f.read(), re.MULTILINE).group(2)

with open('README.md', 'r') as f:
    long_description = f.read()

def read_lines_from_file(filename):
    with open(filename, "r") as f:
        return f.readlines()


if __name__ == '__main__':
    setup(
        name='click-repl',
        version=version,
        description='REPL plugin for Click',
        long_description=long_description,
        long_description_content_type="text/markdown",
        url='https://github.com/click-contrib/click-repl',

        author='Markus Unterwaditzer',
        author_email='markus@unterwaditzer.net',

        license='MIT',
        license_files=('LICENSE',),

        platforms='any',
        keywords=(
            'click', 'click-repl', 'repl', 'click_repl'
        ),

        project_urls={
            'Bug Tracker': 'https://github.com/click-contrib/click-repl/issues',
            'Source Code': 'https://github.com/click-contrib/click-repl/',
            'Documentation': 'https://github.com/click-contrib/click-repl#readme',
        },

        packages=find_packages(where='src'),
        package_dir={
            '': 'src'
        },

        install_requires=read_lines_from_file("./requirements/requirements.txt"),
        extras_require={
            'testing': read_lines_from_file("./requirements/requirements_dev.txt")
        },
        python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',

        zip_safe=True,
        classifiers=[
            "Development Status :: 4 - Beta",
            "Environment :: Console",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: Implementation",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: Terminals",
            "Typing :: Typed",
            'Topic :: Software Development :: Libraries',
            "Topic :: Software Development :: Libraries :: Python Modules",
            'Topic :: Utilities'
        ],
        options={
            'bdist_wheel': {'universal': True}
        }
    )
