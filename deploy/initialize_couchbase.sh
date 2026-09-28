# CREATING CLUSTER

echo "Creating Cluster"

curl -X POST http://${COUCHBASE_HOST}:8091/clusterInit \
  -d clusterName=OpenHealthLakeCluster \
  -d hostname=${COUCHBASE_HOST} \
  -d username=${COUCHBASE_USER} \
  -d password=${COUCHBASE_PASSWORD} \
  -d services=kv,index,n1ql,backup \
  -d dataPath=/opt/couchbase/var/lib/couchbase/data \
  -d indexPath=/opt/couchbase/var/lib/couchbase/data \
  -d analyticsPath=/opt/couchbase/var/lib/couchbase/data \
  -d eventingPath=/opt/couchbase/var/lib/couchbase/data \
  -d memoryQuota=2048 \
  -d indexMemoryQuota=256 \
  -d queryMemoryQuota=512 \
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
  -d ramQuotaMB=2048 \
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
