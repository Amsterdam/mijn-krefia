#!/bin/bash
set -e

# AZ AppService allows SSH into a App instance.
if [ "$MA_CONTAINER_SSH_ENABLED" = "true" ]; then
    echo "Starting SSH ..."
    service ssh start
fi

if [ -n "$ALLEGRO_HOSTS_ENTRY" ]; then
    echo "${ALLEGRO_HOSTS_ENTRY}" >> /etc/hosts
fi

uwsgi --uid www-data --gid www-data --ini /api/uwsgi.ini
