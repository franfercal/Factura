#!/bin/bash

echo "Borrando base de datos actual"
sudo rm -r /home/tics/jair/facturasapp/app/db/facturasapp.sqlite3

echo "Restaurando base de datos nueva"
sudo cp /home/tics/jair/facturasapp/app/deploy/data/facturasapp.sqlite3 /home/tics/jair/facturasapp/app/db/facturasapp.sqlite3

sudo chmod 7777 /home/tics/jair/facturasapp/app/db/facturasapp.sqlite3

sudo supervisorctl restart heytest

echo "Terminado proceso"
