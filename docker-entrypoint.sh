#!/usr/bin/env bash
echo "Start docker-entrypoint.sh"
echo "Environment: ${SENTRY_ENVIRONMENT:=development}"

if [ -n "$ALLEGRO_HOSTS_ENTRY" ]; then
    echo "${ALLEGRO_HOSTS_ENTRY}" >> /etc/hosts
fi

uwsgi --ini /api/uwsgi.ini