#!/bin/sh

# Set user credentials for mc
mc alias set local "http://$MINIO_HOST:$MINIO_PORT" "$MINIO_USER" "$MINIO_PASSWORD"

# Create buckets
mc mb local/lakehouse

# Enable versioning on backups bucket
mc version enable local/lakehouse

# # Set bucket policies
# mc policy set download local/public-data && \
# mc policy set none local/private-data"

echo "Bucket creation complete!"