#!/bin/sh
set -eu

# Alpine's minio-client package installs the command as `mcli`.
mcli alias set local "http://$MINIO_HOST:$MINIO_PORT" "$MINIO_USER" "$MINIO_PASSWORD"

echo "Checking whether bucket 'lakehouse' already exists"
if mcli ls local/lakehouse >/dev/null 2>&1; then
  echo "Bucket 'lakehouse' already exists; skipping MinIO initialization"
  exit 0
fi

# Create buckets
mcli mb local/lakehouse

# Enable versioning on backups bucket
mcli version enable local/lakehouse

# Set bucket policies as needed
# mcli anonymous set download local/public-data

echo "Bucket creation complete!"

exit 0