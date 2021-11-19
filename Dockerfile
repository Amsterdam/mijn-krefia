FROM amsterdam/python as base-app

LABEL maintainer=datapunt@amsterdam.nl

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y
RUN apt-get install nano
RUN pip install --upgrade pip
RUN pip install uwsgi

WORKDIR /app

COPY requirements.txt .
COPY uwsgi.ini .
COPY test.sh .
COPY .flake8 .
COPY scripts ./scripts
COPY app ./app

RUN pip install --no-cache-dir -r ./requirements.txt

FROM base-app as prod-app

COPY docker-entrypoint.sh /app/

ENTRYPOINT /app/docker-entrypoint.sh
