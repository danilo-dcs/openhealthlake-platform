#!/bin/sh

# Script arguments
USER="$1"
PASSWORD="$2"

# Wait for MinIO to be ready
sleep 20

# Set user credentials for mc
mc alias set local http://localhost:9000 "$USER" "$PASSWORD"

# Create buckets
mc mb local/lakehouse

# Enable versioning on backups bucket
mc version enable local/lakehouse

# # Set bucket policies
# mc policy set download local/public-data && \
# mc policy set none local/private-data"

echo "Bucket creation complete!"