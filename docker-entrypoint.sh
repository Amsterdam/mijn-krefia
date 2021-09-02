#!/usr/bin/env bash
echo "Start docker-entrypoint.sh"
echo "Environment: ${SENTRY_ENVIRONMENT:=development}"

uwsgi --uid datapunt --ini /app/uwsgi.ini