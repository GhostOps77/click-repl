# syntax=docker/dockerfile:1

FROM python:3.12.2-slim-bullseye

WORKDIR /home/click-repl
COPY . /home/click-repl

RUN python -m pip install -U tox --no-cache-dir
RUN python3 -m pip install -U pip
RUN pip install -e .[testing]

CMD ["tox", "-r"]
