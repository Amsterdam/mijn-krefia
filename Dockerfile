FROM python:latest as base-app

ENV PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=off

WORKDIR /api

RUN apt-get update \
  && apt-get dist-upgrade -y \
  && apt-get autoremove -y \
  && apt-get install --no-install-recommends -y \
  nano \
  && rm -rf /var/lib/apt/lists/* /var/cache/debconf/*-old \
  && pip install --upgrade pip \
  && pip install uwsgi

COPY requirements.txt /api

RUN pip install -r requirements.txt

COPY ./scripts /api/scripts
COPY ./app /api/app
COPY ./uwsgi.ini /api
COPY ./test.sh /api
COPY .flake8 /api

RUN chmod u+x /api/test.sh

FROM base-app as prod-app

COPY docker-entrypoint.sh /api/

ENTRYPOINT /api/docker-entrypoint.sh
