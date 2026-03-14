#!/bin/sh

MODE="$1"
ADMIN_USER="$2"
ADMIN_PASSWORD="$3"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Checking entries
if [ -z "$MODE" ] || [ -z "$ADMIN_USER" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "Usage: $0 <mode> <admin_username> <admin_password>"
    echo "  <mode>: dev (full application in dev mode), prod (full application in prod mode), or db (database initialization only)"
    echo "  <admin_username>: username for couchbase and minio admin user"
    echo "  <admin_password>: password for couchbase and minio admin user"
    exit 1
fi

export ADMIN_USER="$ADMIN_USER"
export ADMIN_PASSWORD="$ADMIN_PASSWORD"

# adding users to .env
ENV_FILE="$SCRIPT_DIR/.env"

upsert_env() {
    key="$1"
    value="$2"

    if grep -q "^${key}=" "$ENV_FILE"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
        printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    fi
}

[ -f "$ENV_FILE" ] || cp .env.example "$ENV_FILE"

upsert_env "BACKEND_ENV" "$MODE"
upsert_env "COUCHBASE_USER" "$ADMIN_USER"
upsert_env "COUCHBASE_PASSWORD" "$ADMIN_PASSWORD"

# Building images and running containers
if [ "$MODE" = "db" ]; then
    echo "Starting in database initialization mode..."
    sudo -E docker-compose -f docker-compose.yml up -d minio passport-broker couchbase
elif [ "$MODE" = "dev" ]; then
    echo "Starting in development mode..."
    sudo -E docker-compose -f docker-compose.yml up -d couchbase minio passport-broker backend frontend
elif [ "$MODE" = "prod" ]; then
    echo "Starting in production mode..."
    sudo -E docker-compose -f docker-compose.yml up -d couchbase minio passport-broker backend
else
    echo "Invalid mode: $MODE. Use 'dev' or 'prod'."
    exit 1
fi

# Wait for services to be up and running
echo "Waiting for services to start..."
sleep 90

# setup minio
(
    cd "$SCRIPT_DIR/minio"
    sh ./setup.sh
)

# setup couchbase
(
    cd "$SCRIPT_DIR/couchbase/scripts"
    sh ./initialize_couchbase.sh
)

# setup prod frontend
if [ "$MODE" = "prod" ]; then
    sudo apt-get update
    sudo apt-get install -y nodejs npm nginx

    echo "Building frontend dist folder for production..."
    (
        cd "$SCRIPT_DIR/frontend"
        npm install
        npm run build
    )

    sudo mkdir -p /usr/share/nginx/html
    sudo cp -r frontend/lakehouse-ui/dist/* /usr/share/nginx/html/
    sudo systemctl restart nginx

    echo "Testing deployed frontend..."
    if curl -fsS http://localhost >/dev/null; then
        echo "Frontend is reachable via nginx."
    else
        echo "Error: frontend is not being served."
        exit 1
    fi
fi