FROM amsterdam/python:3.8-buster as base-app

LABEL maintainer=datapunt@amsterdam.nl

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y
RUN apt-get install nano
RUN pip install --upgrade pip
RUN pip install uwsgi

WORKDIR /app

COPY /requirements.txt /app/
COPY uwsgi.ini /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY test.sh /app/
COPY .flake8 /app/

COPY krefia /app/krefia

FROM base-app as prod-app

COPY docker-entrypoint.sh /app/

ENTRYPOINT /app/docker-entrypoint.sh
