FROM python:latest as base

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

RUN pip install --upgrade pip \
  && pip install uwsgi \
  && pip install -r requirements.txt

COPY ./scripts /api/scripts
COPY ./app /api/app


FROM base as tests

COPY conf/test.sh /api/
COPY .flake8 /api/

RUN chmod u+x /api/test.sh

ENTRYPOINT [ "/bin/sh", "/api/test.sh"]


FROM base as publish

# ssh ( see also: https://github.com/Azure-Samples/docker-django-webapp-linux )
ENV SSH_PASSWD "root:Docker!"
RUN apt-get update \
  && apt-get install -y --no-install-recommends dialog \
  && apt-get update \
  && apt-get install -y --no-install-recommends openssh-server \
  && echo "$SSH_PASSWD" | chpasswd 

EXPOSE 8000
ENV PORT 8000

COPY conf/uwsgi.ini /api/
COPY conf/docker-entrypoint.sh /api/
COPY conf/sshd_config /etc/ssh/

RUN chmod u+x /api/docker-entrypoint.sh

ENTRYPOINT [ "/bin/sh", "/api/docker-entrypoint.sh"]

FROM publish as publish-final

COPY /files /app/files
