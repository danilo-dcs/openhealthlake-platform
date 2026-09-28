#!/bin/sh

set -eu

MODE="${1:-}"

# Checking entries
if [ -z "$MODE" ]; then
    echo "Usage: $0 <mode>" >&2
    echo "Mode should be one of the following: dev | prod"
    exit 1
fi

case "$MODE" in
    prod) 
        COMPOSE_FILE="docker-compose.prod.yml" 
        echo "Production mode selected..."
        ;;
    dev)  
        COMPOSE_FILE="docker-compose.dev.yml" 
        echo "Development mode selected..."
        ;;
    *)
        echo "Invalid mode: $MODE. Expected dev or prod." >&2
        exit 1
        ;;
esac

export LAKEHOUSE_USER="$ADMIN_USER"
export LAKEHOUSE_PASSWORD="$ADMIN_PASSWORD"

WK_DIR="$(pwd)"

echo "Building application conteiners ..."
sudo -E docker-compose -f "$COMPOSE_FILE" --env-file "$WK_DIR" up --build -d couchbase minio passport-broker backend frontend


# Wait for services to be up and running
echo "Waiting for services to start..."
sleep 90

# seutp minio
echo "Initializing MinIO ..."
sudo chmod +x ./minio/setup.sh
./minio/setup.sh

# seutp couchbase
echo "initializing couchbase ..."
sudo chmod +x ./couchbase/initialize_couchbase.sh
./couchbase/initialize_couchbase.sh