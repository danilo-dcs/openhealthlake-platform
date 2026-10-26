from fastapi import APIRouter, Depends

from routes.auth_routes import auth_oauth2_scheme
from services.StatsServices import StatsServices
from shared.models.stats import (
    CollectionVisibilityStatsResponse,
    FileProcessingStatsResponse,
    TotalStatsResponse,
)


router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get(path="/buckets", response_model=TotalStatsResponse)
async def get_bucket_stats(
    _: str = Depends(auth_oauth2_scheme),
) -> TotalStatsResponse:
    return await StatsServices().get_bucket_total()


@router.get(path="/collections/total", response_model=TotalStatsResponse)
async def get_collection_total_stats(
    _: str = Depends(auth_oauth2_scheme),
) -> TotalStatsResponse:
    return await StatsServices().get_collection_total()


@router.get(path="/collections/visibility", response_model=CollectionVisibilityStatsResponse)
async def get_collection_visibility_stats(
    _: str = Depends(auth_oauth2_scheme),
) -> CollectionVisibilityStatsResponse:
    return await StatsServices().get_collection_visibility()


@router.get(path="/files", response_model=TotalStatsResponse)
async def get_file_stats(
    _: str = Depends(auth_oauth2_scheme),
) -> TotalStatsResponse:
    return await StatsServices().get_file_total()


@router.get(path="/files/category", response_model=FileProcessingStatsResponse)
async def get_file_category_stats(
    _: str = Depends(auth_oauth2_scheme),
) -> FileProcessingStatsResponse:
    return await StatsServices().get_file_processing_levels()
