"""Generation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.repositories.program_repository import ProgramRepository
from app.schemas.generation import AdResult, GenerationRequest, GenerationResponse
from app.services.naming_service import NamingService
from app.services.onelink_service import OneLinkService
from app.schemas.auth import AuthenticatedUser

router = APIRouter()


@router.post(
    "/all",
    response_model=GenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="批量生成所有结果",
    description="根据输入的 Campaign、Ad Set 和 Ad 字段，生成 Campaign Name、Ad Set Name、多个 Ad Name 和对应的 OneLink URL。",
)
async def generate_all(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> GenerationResponse:
    """
    Generate all naming and OneLink URLs in batch.
    
    This endpoint:
    1. Fetches Program Info from repository
    2. Generates Campaign Name using NamingService
    3. Generates Ad Set Name using NamingService
    4. Generates multiple Ad Names using NamingService
    5. Generates corresponding OneLink URLs using OneLinkService
    
    Returns:
        GenerationResponse containing campaign name, ad set name, and ad results
    """
    # Get Program Info from repository
    repository = ProgramRepository(db)
    all_programs = await repository.get_all_programs()
    
    # Find the program by program_code
    program_info = None
    for program in all_programs:
        if program.program_code == request.program_code:
            program_info = program
            break
    
    if not program_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program with code '{request.program_code}' not found",
        )
    
    # Extract user email prefix from authenticated user
    user_email_prefix = current_user.email_prefix
    
    # Generate Campaign Name
    campaign_name = NamingService.generate_campaign_name(
        country=request.campaign.country,
        media_source=request.campaign.media_source,
        mkt_type=request.campaign.mkt_type,
        target_type=request.campaign.target_type,
        optimization_types=request.campaign.optimization_types,
        os=request.campaign.os,
        program_code=program_info.program_code,
        program_shortner=program_info.program_shortner,
        title_en_shortener=program_info.title_en_shortener,  # Prefer this if program_shortner is empty
        title=program_info.title,  # Fallback if title_en_shortener is empty
        event_type=request.campaign.event_type,
        user_email_prefix=user_email_prefix,
        optional_campaign=request.campaign.optional_campaign,
    )
    
    # Generate Ad Set Name (新命名规则 v2)
    # 格式: app-vigloo_{国家}_{语言}_{传媒资源}_{路径类型}_{优化器}_{日期}_{剧集}_{事件}_{其他}
    ad_set_name = NamingService.generate_adset_name_v2(
        country=request.adset.country,
        language=request.adset.language,
        media_source=request.adset.media_source,
        os=request.adset.os,
        optimizer=request.adset.optimizer,
        date=request.adset.date,
        drama_id=request.adset.drama_id,
        event=request.adset.event,
        optional=request.adset.optional,
    )

    # Prepare ads data for batch generation (新命名规则 v2)
    # 格式: {戏剧ID}_{语言}_{团队}_{设计师}_{日期}_{类型}_{数字}_{其他}
    ads_data = []
    for ad in request.ads:
        ads_data.append({
            "drama_id": ad.drama_id,
            "language": ad.language,
            "team": ad.team,
            "designer": ad.designer,
            "date": ad.date,
            "creative_type": ad.creative_type,
            "number": ad.number,
            "optional": ad.optional,
        })

    # Generate Ad Names in batch (新命名规则 v2)
    ad_names = NamingService.generate_ad_names_v2(ads=ads_data)
    
    # Prepare ads data for OneLink generation (need onelinkLanguage and onelinkIntroEpNo)
    onelink_ads_data = []
    for ad in request.ads:
        onelink_ads_data.append({
            "onelinkLanguage": ad.onelink_language,  # Use onelink_language for OneLink URL generation
            "onelinkIntroEpNo": ad.onelink_intro_ep_no or "1",  # Use Onelink Intro Ep No, default to "1"
        })
    
    # Get base URL (from program_info if available, otherwise use default)
    # Note: base_one_link_url and fixed_params are not currently in ProgramInfo schema
    # They can be added later if needed from Google Sheets
    base_url = OneLinkService.BASE_URL
    
    # Get season_id (handle None case - season_id is optional in ProgramInfo)
    season_id = program_info.season_id or ""
    
    # Generate OneLink URLs in batch
    try:
        onelink_urls = OneLinkService.generate_onelink_urls(
            base_url=base_url,
            media_source=request.campaign.media_source,
            campaign_name=campaign_name,
            adset_name=ad_set_name,
            ad_names=ad_names,
            program_id=program_info.program_id,
            season_id=season_id,
            ads=onelink_ads_data,
            fixed_params=None,  # TODO: Add fixed_params to ProgramInfo schema if needed
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Build response
    # Use AdResult objects to ensure proper serialization with aliases
    ad_results = [
        AdResult(ad_name=ad_name, one_link_url=onelink_url)
        for ad_name, onelink_url in zip(ad_names, onelink_urls)
    ]
    
    return GenerationResponse(
        campaign_name=campaign_name,
        ad_set_name=ad_set_name,
        ad_results=ad_results,
    )

