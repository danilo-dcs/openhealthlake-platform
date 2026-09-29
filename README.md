# Lakehouse Platform (OpenHealthLake)

This lakehouse platfrom is fully open-source and adaptable. It was built to help low-resourced research groups and health initiatives on addressing the challenges adhered from heterogeneous data management, data sharing and data governance. It was implemented as part of a MSc in Computer Science project, supported by the Stellenbosch University (South Africa), the [Centre for Epidemic Response and Innovation](https://ceri.org.za/), and the [INFORM Africa Research Study Group](https://inform-africa.org/).

It is important to highlight that this is a prototype platform which is still under development. It can be used as a supplementary tool to support data storage, data sharing, and data governance. Efforts to implement tools to support workflows and analytical processing analysis will be put in to expant this platform in the near future. 

Currently, the Currently, there is an instance of this prototype platform available at ([OpenHealthLake](https://openhealthlake.pathotrack.health/login)).


## Platform Structure

This first prototype platform's design is based on the data lakehouse architecture, adapted to focus on data storage and governance. The design comprised three main components: _Data Storare_, _Application Database_, and a _Application API_ (as shown in the Diagram below).

![Storage Structure](./figures/lakehouse_structure.png)

The data storage component supports three storage environments, including Google Cloud Storage, Amazon S3 and Apache HDFS. The physical files are grouped in dataset collections (folders or repositories of files) and stored in these environments. The platform supports the distinction between raw and processed files. The access is granted at a collection level, which means that data owners can create collections with one or multiple files and grant extarnal users access to their collections.

The application database component stores all data necessary to control the platform's execution flow and governance, including user data, permission data, external storage environment access keys and the data catalogue (which comprises a list of physical files and a list of collections). This database is implemented with the Non-relational database Couchbase, which is easy to set up, and to scale up and down. Couchbase can be installed using docker containers and provides flexibility to adapt to different computational environments, ranging from single cluster to multicluster environments.

Lastly, the application API controls the execution flow of funtionalities, besides encapsulating the application core business logic such as authentication, access control, data uploading, data downloading, and data versioning. It can be accessed by external services and by additional Python ([see documentation](https://github.com/danilo-dcs/lakehouse-python-package)) and R ([see documentation](https://github.com/danilo-dcs/lakehouse-R-package)) libraries built to support interoperability from user's runtime environments.


## Platform/Repository Access Index

- [Lakehouse API Code](./backend/)
- [Lakehouse Web Interface Code](./frontend/)
- [Initializing scripts for standalone deploy](./deploy/)



## Lauching a Standalone Platform

1. Navigate to [MinIO AIStor website](https://www.min.io/download), and request the free licence.

2. Crewte a new `minio.licence` file in this repository's root directory `./`, copy and paste the license into this file.
```shell
echo "PASTE_YOUR_LICENSE" > minio.licence
```

3. Copy the `.env.example` file in the `root/` directory into a `.env` file.
```shell
cp .env.example .env
```

4. Fill in the `.env` file.
    - `EMAIL_SERVICE_KEY` should contain a generated API key from [Resend mailing service](https://resend.com/api-keys)
    - `COUCHBASE_USER` and `COUCHBASE_PASSWORD` indicate Couchbase's admin credentials.
    - `COUCHBASE_HOST` and `COUCHBASE_BUCKET` indicate the location for the new application bucket to be initialized. `COUCHBASE_HOST` value should be `couchbase` for docker lauched environments.
    - `MINIO_USER` and `MINIO_PASSWORD` indicate MinIO's admin credentials.
    - The encryption keys should be generated with the command `openssl rand -hex 32` and then pasted into the `.env` file. 
    - The `ENCRYPTION_SECRET_KET`, `AUTH_SECRET_KEY`, and `REFRESH_TOKEN_KEY` must have their own dedicated encryption key.

5. Copy the dedicated `.env.example` file in the `frontend/` directory into a `.env` file.
```shell
cp frontend/.env.example frontend/.env
```

6. Fill in the frontend's `.env` file.

7. Run the command below:
```shell
docker-compose up -d --build
```
