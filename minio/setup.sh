#!/bin/sh

sudo chmod +x ./initialize_minio.sh

./initialize_minio.sh ${LAKEHOUSE_USER} ${LAKEHOUSE_PASSWORD}