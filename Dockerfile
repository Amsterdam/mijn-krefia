# echo "10.204.22.40 schuldhulp-ft.sociaal.amsterdam.nl" >> /etc/hosts

FROM amsterdam/python

LABEL maintainer=datapunt@amsterdam.nl

ENV PYTHONUNBUFFERED 1

EXPOSE 8000

RUN apt-get update && apt-get install -y
RUN pip install --upgrade pip
RUN pip install uwsgi

WORKDIR /app

COPY test.sh /app/
COPY .flake8 /app/
COPY requirements.txt /app/
COPY uwsgi.ini /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY krefia /app/krefia

USER datapunt
CMD uwsgi --ini /app/uwsgi.ini
