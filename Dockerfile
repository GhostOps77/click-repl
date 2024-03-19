# syntax=docker/dockerfile:1

FROM ubuntu:focal

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends software-properties-common
RUN add-apt-repository -y 'ppa:deadsnakes/ppa'
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3.6 python3.7 python3.8 python3.8-venv python3.9 python3.10 python3.11 python3.12 python3.13
RUN rm -rf /var/lib/apt/lists/*

ADD . /home/click-repl
WORKDIR /home/click-repl

ENV PATH=/venv/bin:$PATH
RUN python3.8 -m venv /venv
RUN python -m pip install --upgrade tox --no-cache-dir

RUN python3 -m pip install -U pip
RUN pip install -e .[testing]

CMD ["tox", "-r"]
EXPOSE 3000
