"""Program information schemas."""

from datetime import date
from typing import List

from pydantic import BaseModel, Field


class ProgramInfo(BaseModel):
    """Program information returned by Program API."""

    program_code: str = Field(..., alias="programCode", description="Program Code")
    program_id: str = Field(..., alias="id", description="Program ID")
    title: str = Field(..., description="English title")
    sub_title: str = Field("", alias="subTitle", description="English subtitle")
    synopsis: str = Field("", description="English synopsis")
    episode_count: int = Field(..., alias="episodeCount", description="Total episode number")
    release_date: date | None = Field(None, alias="releaseDate", description="Release date")
    content_information: str = Field(
        "",
        alias="contentInformation",
        description="Content advisory information",
    )
    program_shortner: str = Field("", alias="shortener", description="Program Shortener from All sheet")
    title_en_shortener: str = Field("", description="Title(EN/Shortener), defaults to title if shortener is empty")
    season_id: str | None = Field(None, alias="seasonId", description="Season ID from All sheet (optional)")

    model_config = {"populate_by_name": True}


class ProgramListResponse(BaseModel):
    """Paginated response for program list."""

    items: List[ProgramInfo]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, alias="pageSize")

    model_config = {"populate_by_name": True}
