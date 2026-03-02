#!/bin/sh

ADMIN_USER="$1"
ADMIN_PASSWORD="$2"

# Checking entries
if [ -z "$ADMIN_USER" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "Usage: $0 <admin_username> <admin_password>"
    exit 1
fi

export USER="$ADMIN_USER"
export PASSWORD="$ADMIN_PASSWORD"

# Building images and running containers
sudo -E docker-compose -f docker-compose.yml up -d couchbase minio passport-broker backend frontend

# Wait for services to be up and running
echo "Waiting for services to start..."
sleep 90

# seutp minio
sudo chmod +x ./minio/setup.sh
./minio/setup.sh

sudo chmod +x ./couchbase/initialize_couchbase.sh
./couchbase/initialize_couchbase.sh