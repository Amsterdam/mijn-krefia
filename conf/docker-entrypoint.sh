#!/usr/bin/env bash
set -e

# echo "Starting SSH ..."
service ssh start

echo "Start docker-entrypoint.sh"
echo "Environment: ${SENTRY_ENVIRONMENT:=development}"

if [ -n "$ALLEGRO_HOSTS_ENTRY" ]; then
    echo "${ALLEGRO_HOSTS_ENTRY}" >> /etc/hosts
fi

uwsgi --uid www-data --gid www-data --ini /api/uwsgi.ini