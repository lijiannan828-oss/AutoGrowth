"""Generation request and response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CampaignFields(BaseModel):
    """Campaign level fields."""

    country: str = Field(..., description="Country code (e.g., 'us', 'kr', 'jp')")
    media_source: str = Field(..., alias="mediaSource", description="Media source (e.g., 'fb', 'go', 'tt')")
    mkt_type: str = Field(..., alias="mktType", description="Market type (e.g., 'ua')")
    target_type: Optional[str] = Field(None, alias="targetType", description="Target type (e.g., 'auto')")
    optimization_types: str = Field(..., alias="optimizationTypes", description="Optimization type (e.g., 'purchase', 'install', 'watch')")
    os: str = Field(..., description="Operating system (e.g., 'w2a', 'ios', 'and')")
    event_type: Optional[str] = Field(None, alias="eventType", description="Event type (optional)")
    optional_campaign: Optional[str] = Field(None, alias="optionalCampaign", description="Optional campaign remark (e.g., 'han')")

    model_config = {"populate_by_name": True}


class AdSetFields(BaseModel):
    """Ad Set level fields - 新命名规则.

    格式: app-vigloo_{国家}_{语言}_{传媒资源}_{路径类型}_{优化器}_{日期}_{剧集}_{事件}_{其他}
    例子: App-vigloo_us_en_fb_w2a_jade_1000325_purchase_v1
    """

    country: str = Field(..., description="Country code (e.g., 'us', 'ww', 'kr')")
    language: str = Field(..., description="Language code (e.g., 'en', 'es', 'kr')")
    media_source: str = Field(..., alias="mediaSource", description="Media source (e.g., 'fb', 'tt', 'go')")
    os: str = Field(..., description="Path type / OS (e.g., 'w2a', 'ios', 'and')")
    optimizer: str = Field(..., description="Optimizer name (e.g., 'jade', 'kino', 'silas')")
    date: str = Field(..., description="Date in format MMDD or YYMMDD (e.g., '1205', '1000325')")
    drama_id: str = Field(..., alias="dramaId", description="Drama/Program ID (e.g., '10000235')")
    event: str = Field(..., description="Event type (e.g., 'purchase', 'install')")
    optional: Optional[str] = Field(None, description="Optional suffix (e.g., 'v1', 'v2')")

    model_config = {"populate_by_name": True}


class AdFields(BaseModel):
    """Ad level fields - 新命名规则.

    格式: {戏剧ID}_{语言}_{团队}_{设计师}_{日期}_{类型}_{数字}_{其他}
    团队: vc (vigloo cn), vk (vigloo kr), cj (代理)
    例子:
    - 10000235_en_vc_eason_1205_hilight_01
    - 10000234_kr_vk_juria_1205_episode_01-05_txt
    - 10000234_kr_cj_juria_1205_episode_01-05_ctn
    """

    drama_id: str = Field(..., alias="dramaId", description="Drama/Program ID (e.g., '10000235')")
    language: str = Field(..., description="Language code (e.g., 'en', 'kr', 'jp')")
    team: str = Field(..., description="Team code: vc (vigloo cn), vk (vigloo kr), cj (代理)")
    designer: str = Field(..., description="Designer name (e.g., 'eason', 'kyrie', 'beita')")
    date: str = Field(..., description="Date in format MMDD (e.g., '1205')")
    creative_type: str = Field(..., alias="creativeType", description="Creative type (e.g., 'hilight', 'episode', 'teaser')")
    number: Optional[str] = Field(None, description="Number or range (e.g., '01', '01-05')")
    optional: Optional[str] = Field(None, description="Optional suffix (e.g., 'txt', 'ctn')")

    # OneLink 相关字段
    onelink_intro_ep_no: str = Field("1", alias="onelinkIntroEpNo", description="Onelink Intro Ep No (required, default '1')")
    onelink_language: str = Field(..., alias="onelinkLanguage", description="Onelink Language (e.g., 'en', 'ko', 'ja', 'id', 'zh') - for OneLink URL generation")

    model_config = {"populate_by_name": True}

    @field_validator("team")
    @classmethod
    def validate_team(cls, v: str) -> str:
        """Validate team code."""
        valid_teams = ["vc", "vk", "cj"]
        if v.lower() not in valid_teams:
            raise ValueError(f"Team must be one of: {valid_teams}")
        return v.lower()

    @field_validator("onelink_language")
    @classmethod
    def validate_onelink_language(cls, v: str) -> str:
        """Validate onelink language is not empty."""
        if not v or not v.strip():
            raise ValueError("Onelink Language is required")
        return v.strip()


class GenerationRequest(BaseModel):
    """Request schema for generation API."""

    program_code: str = Field(..., alias="programCode", description="Program Code")
    campaign: CampaignFields
    adset: AdSetFields
    ads: List[AdFields] = Field(..., description="List of Ad fields (max 30)")

    model_config = {"populate_by_name": True}

    @field_validator("ads")
    @classmethod
    def validate_ads(cls, v: List[AdFields]) -> List[AdFields]:
        """Validate ads count and required fields."""
        if not v:
            raise ValueError("At least one Ad is required")
        if len(v) > 30:
            raise ValueError(f"Maximum 30 ads allowed, got {len(v)}")

        # Validate conditional required fields for each ad
        for i, ad in enumerate(v):
            # Validate onelink_intro_ep_no (always required)
            if not ad.onelink_intro_ep_no or not ad.onelink_intro_ep_no.strip():
                raise ValueError(f"Ad {i + 1}: Onelink Intro Ep No is required")

        return v


class AdResult(BaseModel):
    """Single Ad generation result."""

    ad_name: str = Field(..., alias="adName", description="Generated Ad Name")
    one_link_url: str = Field(..., alias="oneLinkUrl", description="Generated OneLink URL")

    model_config = {"populate_by_name": True}


class GenerationResponse(BaseModel):
    """Response schema for generation API."""

    campaign_name: str = Field(..., alias="campaignName", description="Generated Campaign Name")
    ad_set_name: str = Field(..., alias="adSetName", description="Generated Ad Set Name")
    ad_results: List[AdResult] = Field(..., alias="adResults", description="List of Ad results (each contains adName and oneLinkUrl)")

    model_config = {"populate_by_name": True}

