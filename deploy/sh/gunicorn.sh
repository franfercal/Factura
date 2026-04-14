#!/bin/bash

# Nombre del proceso Gunicorn (visible en ps / logs).
NAME="facturasapp"
DJANGO_DIR=$(dirname $(dirname $(cd `dirname $0` && pwd)))
SOCKFILE=/tmp/gunicorn.sock
LOG_DIR=${DJANGO_DIR}/logs/gunicorn.log
USER=jair
GROUP=jair
NUM_WORKERS=5
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_WSGI_MODULE=config.wsgi
TIMEOUT=600000

rm -frv $SOCKFILE

echo $DJANGO_DIR
cd $DJANGO_DIR
echo "Iniciando la aplicación $NAME con el usuario `whoami`"

exec ${DJANGO_DIR}/venv/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --timeout $TIMEOUT \
  --user=$USER --group=$GROUP \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=$LOG_DIR