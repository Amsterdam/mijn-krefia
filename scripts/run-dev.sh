#!/usr/bin/env bash

export FLASK_ENV=development
export FLASK_APP=./app/server.py
export MA_OTAP_ENV=development

flask run
