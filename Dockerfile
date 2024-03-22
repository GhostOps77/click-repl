# syntax=docker/dockerfile:1

FROM python:3.12.2-slim-bullseye

ADD . /home/click-repl
WORKDIR /home/click-repl

RUN python -m pip install -U tox --no-cache-dir
RUN python3 -m pip install -U pip
RUN pip install -e .[testing]

CMD ["tox", "-r"]
# EXPOSE 3000
