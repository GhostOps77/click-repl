# syntax=docker/dockerfile:1

FROM python:3.11.4-slim
# COPY . /click-repl
ADD . /home/click-repl
WORKDIR /home/click-repl
RUN python3 -m pip install -U pip
# RUN pip install -e .[testing]
RUN pip install click==6.7
CMD ["tail", "-f", "/dev/null"]
EXPOSE 3000
