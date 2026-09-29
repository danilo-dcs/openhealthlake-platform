# CREATING CLUSTER

set -eu

echo "Checking whether bucket '${COUCHBASE_BUCKET}' is already initialized"
if curl --fail --silent \
  --user "${COUCHBASE_USER}:${COUCHBASE_PASSWORD}" \
  "http://${COUCHBASE_HOST}:8091/pools/default/buckets" \
  >/dev/null; then
  echo "Bucket '${COUCHBASE_BUCKET}' already exists; skipping Couchbase initialization"
  exit 0
fi

echo "Creating Cluster"

curl --fail -X POST http://${COUCHBASE_HOST}:8091/clusterInit \
  -d clusterName=OpenHealthLakeCluster \
  -d hostname=${COUCHBASE_NODE_HOSTNAME} \
  -d username=${COUCHBASE_USER} \
  -d password=${COUCHBASE_PASSWORD} \
  -d services=kv,index,n1ql,backup \
  -d dataPath=/opt/couchbase/var/lib/couchbase/data \
  -d indexPath=/opt/couchbase/var/lib/couchbase/data \
  -d analyticsPath=/opt/couchbase/var/lib/couchbase/data \
  -d eventingPath=/opt/couchbase/var/lib/couchbase/data \
  -d memoryQuota=${COUCHBASE_TOTAL_MEMORY_QUOTA} \
  -d indexMemoryQuota=$((COUCHBASE_TOTAL_MEMORY_QUOTA * 1 / 4)) \
  -d queryMemoryQuota=$((COUCHBASE_TOTAL_MEMORY_QUOTA * 1 / 4)) \
  -d nodeEncryption=on \
  -d indexerStorageMode=plasma \
  -d port=SAME

sleep 10

# curl -u admin:admin1234 -X POST http://${COUCHBASE_HOST}:8091/settings/indexes \
#   -d 'storageMode=plasma'

echo "$(curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} http://localhost:8091/settings/indexes)"

echo "Creating Bucket"

# CREATING BUCKET
sleep 15
curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets \
  -d name=${COUCHBASE_BUCKET} \
  -d ramQuotaMB=$((COUCHBASE_TOTAL_MEMORY_QUOTA * 3 / 4)) \
  -d bucketType=couchbase

echo "Creating Scopes"

# CREATING SCOPES
sleep 10
curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes \
  -d name=catalogs

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes \
  -d name=users

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes \
  -d name=credentials

echo "Creating Collections"

# CREATING COLLECTIONS
sleep 5
curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes/catalogs/collections -d name=files 

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes/catalogs/collections -d name=collections

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes/credentials/collections -d name=cloud

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes/credentials/collections -d name=hadoop

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes/users/collections -d name=info

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes/users/collections -d name=visa

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8091/pools/default/buckets/lakehouse/scopes/users/collections -d name=access_requests

echo "Creating Indexes"

#CREATING INDEXES
sleep 5
curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8093/query/service \
  -d 'statement=CREATE PRIMARY INDEX ON `lakehouse`.`catalogs`.`collections`'

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8093/query/service \
  -d 'statement=CREATE PRIMARY INDEX ON `lakehouse`.`catalogs`.`files`'

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8093/query/service \
  -d 'statement=CREATE PRIMARY INDEX ON `lakehouse`.`credentials`.`cloud`'

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8093/query/service \
  -d 'statement=CREATE PRIMARY INDEX ON `lakehouse`.`credentials`.`hadoop`'

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8093/query/service \
  -d 'statement=CREATE PRIMARY INDEX ON `lakehouse`.`users`.`info`'

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8093/query/service \
  -d 'statement=CREATE PRIMARY INDEX ON `lakehouse`.`users`.`visa`'

curl -u ${COUCHBASE_USER}:${COUCHBASE_PASSWORD} -X POST http://${COUCHBASE_HOST}:8093/query/service \
  -d 'statement=CREATE PRIMARY INDEX ON `lakehouse`.`users`.`access_requests`'


exit 0