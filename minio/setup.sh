#!/bin/sh

# sudo chmod +x ./initialize_minio.sh
set -eu

sh ./initialize_minio.sh ${ADMIN_USER} ${ADMIN_PASSWORD}