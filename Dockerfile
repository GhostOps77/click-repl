# # syntax=docker/dockerfile:1

# FROM ubuntu:focal

# RUN apt-get update
# RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends software-properties-common
# RUN add-apt-repository -y 'ppa:deadsnakes/ppa'
# RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3.11
# RUN rm -rf /var/lib/apt/lists/*

FROM python:3.12.2-slim

ADD . /home/click-repl
WORKDIR /home/click-repl

# ENV PATH=/venv/bin:$PATH
# RUN python3.11 -m venv /venv
RUN python -m pip install -U tox --no-cache-dir

RUN python3 -m pip install -U pip
RUN pip install -e .[testing]

CMD ["tox", "-r"]
EXPOSE 3000
