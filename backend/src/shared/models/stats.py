from pydantic import BaseModel


class TotalStatsResponse(BaseModel):
    total: int


class CollectionVisibilityStatsResponse(BaseModel):
    public: int
    private: int


class FileProcessingStatsResponse(BaseModel):
    raw: int
    processed: int
    curated: int
