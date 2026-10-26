from shared.models.env import EnvSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# import sys
# from pathlib import Path

# sys.path.append(str(Path(__file__).resolve().parent))

import init_env  # noqa: F401

from routes.auth_routes import router as auth_router
from routes.catalog_routes import router as catalog_router
from routes.credential_routes import router as credentials_router
from routes.storage_routes import router as storage_router
from routes.user_routes import router as users_router
# from routes.visa_routes import router as visas_router
from routes.access_request_routes import router as access_request_routes
from routes.stats_routes import router as stats_router

from starlette.middleware.base import BaseHTTPMiddleware

from middlewares.AuthMiddleware import authentication_middleware


settings = EnvSettings()

is_prod = settings.BACKEND_ENV == "prod"

app = FastAPI(
    title="Lakehouse API",
    version="1.0.0",
    docs_url="/docs" if is_prod else "/docs",        # same
    openapi_url="/openapi.json" if is_prod else "/openapi.json",
    root_path="",                                 
    servers=[
        {"url": "/", "description": "Local Development"},
        {"url": "/api", "description": "Production via NGINX Reverse Proxy"},
    ],
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],
#     allow_origin_regex=r"https:\/\/.*\.pathotrack\.health",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",  # allows all but compatible w/ credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.middleware("http")(authentication_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=authentication_middleware)

app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(access_request_routes)
app.include_router(credentials_router)
app.include_router(storage_router)
app.include_router(users_router)
app.include_router(stats_router)
# app.include_router(visas_router)
