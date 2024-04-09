FROM python:3.11-slim-bookworm as base
MAINTAINER Eduard Pinconschi <eduard.pinconschi@tecnico.ulisboa.pt>
ARG mode=dev
ENV PS1="\[\e[0;33m\]|> tenet <| \[\e[1;35m\]\W\[\e[0m\] \[\e[0m\]# "

FROM base as dev
WORKDIR /src
COPY . /src
RUN --mount=type=cache,mode=0777,target=/root/.cache/pip \
    pip install build && python -m build \
    #pip install -r requirements.txt \
    && pip install . && ./setup.sh
WORKDIR /
ENTRYPOINT ["tenet"]

FROM base as prod
WORKDIR /src
COPY . /src
RUN pip install --no-cached-dir -r requirements.txt \
&& pip install . && ./setup.sh
WORKDIR /
ENTRYPOINT ["tenet"]