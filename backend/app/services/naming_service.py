"""Naming service for generating Campaign, Ad Set, and Ad names according to SOP rules.

新命名规则:
广告组: app-vigloo_{国家}_{语言}_{传媒资源}_{路径类型}_{优化器}_{日期}_{剧集}_{事件}_{其他}
广告: {戏剧ID}_{语言}_{团队}_{设计师}_{日期}_{类型}_{数字}_{其他}
"""

import re
from typing import List

from app.utils.mappings import get_optimization_abbreviation, get_optimization_naming


def normalize_for_naming(text: str) -> str:
    """
    Normalize text for naming generation.

    Replaces all spaces with underscores, converts to lowercase, and removes extra whitespace.

    Args:
        text: Input text (may contain spaces)

    Returns:
        Normalized text with spaces replaced by underscores and converted to lowercase
    """
    if not text:
        return ""
    # Replace all whitespace (spaces, tabs, etc.) with underscores and convert to lowercase
    normalized = re.sub(r'\s+', '_', text.strip()).lower()
    return normalized


class NamingService:
    """Service for generating names according to SOP rules."""
    
    @staticmethod
    def generate_campaign_name(
        country: str,
        media_source: str,
        mkt_type: str,
        target_type: str | None,
        optimization_types: str,
        os: str,
        program_code: str,
        program_shortner: str,
        title_en_shortener: str,
        title: str,
        event_type: str | None,
        user_email_prefix: str,
        optional_campaign: str | None,
    ) -> str:
        """
        Generate Campaign Name according to SOP rules.
        
        Format: [Country]_[Media source]_[Mkt type]_[Target type]_[Optimization abbreviation]_[Optimization types]_[OS]_[Program code]_[Program shortner/Title]_[Event type]_cn_[User email prefix]_[Optional (Campaign)]
        
        Empty fields are intelligently skipped (no underscore added).
        Program shortner: If not found, use Title as fallback (normalized with underscores).
        'cn' is added before User email prefix to indicate team affiliation.
        User email prefix is automatically appended after 'cn' and before Optional (Campaign).
        
        Args:
            country: Country code (e.g., 'us', 'jp', 'kr', 'id', 'th')
            media_source: Media source (e.g., 'fb', 'go', 'tt')
            mkt_type: Market type (e.g., 'ua')
            target_type: Target type (e.g., 'auto') or None
            optimization_types: Optimization type (e.g., 'purchase', 'install', 'watch')
            os: Operating system (e.g., 'w2a', 'ios', 'and')
            program_code: Program Code (e.g., 'KR000P05S01')
            program_shortner: Program shortner (e.g., 'romantic_island') or empty string
            title: Title from En sheet (used as fallback if program_shortner is empty)
            event_type: Event type (optional)
            user_email_prefix: User email prefix (e.g., 'user' from 'user@company.com')
            optional_campaign: Optional campaign remark (e.g., 'han') or None
        
        Returns:
            Generated Campaign Name
        """
        parts: List[str] = []
        
        # Required fields
        parts.append(country)
        parts.append(media_source)
        parts.append(mkt_type)
        
        # Optional target_type
        if target_type:
            parts.append(target_type)
        
        # Optimization abbreviation (derived from optimization_types)
        # install -> [i], others -> [e]
        opt_abbr = get_optimization_abbreviation(optimization_types)
        parts.append(opt_abbr)
        
        # Optimization types (subscription -> subs, others as-is)
        opt_naming = get_optimization_naming(optimization_types)
        parts.append(opt_naming)
        
        # OS
        parts.append(os)
        
        # Program code
        parts.append(program_code)
        
        # Program shortner/title (priority: program_shortner -> title_en_shortener -> title)
        # Values are normalized/converted to lowercase
        if program_shortner:
            parts.append(program_shortner.lower())
        else:
            # Prefer Title(EN/Shortener); if empty, fallback to Title
            candidate_title = title_en_shortener if title_en_shortener else title
            parts.append(normalize_for_naming(candidate_title))
        
        # Optional event_type
        if event_type:
            parts.append(event_type)
        
        # Add 'cn' before user email prefix to indicate team affiliation
        parts.append("cn")
        
        # User email prefix (only added if provided)
        if user_email_prefix:
            parts.append(user_email_prefix)
        
        # Optional campaign remark
        if optional_campaign:
            parts.append(optional_campaign)
        
        return "_".join(parts)
    
    @staticmethod
    def generate_adset_name(campaign_name: str, optional_adset: str) -> str:
        """
        Generate Ad Set Name based on Campaign Name.
        
        Format: [Generated Campaign Name]_[Optional (Ad Set)]
        
        Args:
            campaign_name: Generated Campaign Name
            optional_adset: Optional Ad Set identifier (required, e.g., 'test01')
        
        Returns:
            Generated Ad Set Name
        """
        if not optional_adset:
            raise ValueError("Optional (Ad Set) is required")
        
        return f"{campaign_name}_{optional_adset}"
    
    @staticmethod
    def generate_ad_name(
        program_code: str,
        title_en_shortener: str,
        creative_type: str,
        number: str | None,
        intro_ep_no: str | None,
        text_included: bool,
        concept_keyword: str | None,
        language: str,
        user_email_prefix: str = "",
    ) -> str:
        """
        Generate Ad Name according to SOP rules.
        
        Format: video_[Program code]_[Title(EN/Shortener)]_[creative type]_[Number]_[Intro Ep No]_[Text included]_[concept keyword_intro]_[Language]_cn_[User email prefix]
        
        Conditional fields are intelligently skipped:
        - Number: Only included when creative_type='highlight' or 'epi', otherwise skipped
        - Intro Ep No: Only included when creative_type='highlight' or 'epi', otherwise skipped
        - Text included: If true, value is 'txt', otherwise skipped (including underscore)
        - concept keyword: If empty, skipped (including underscore and "_intro" suffix)
        
        Fixed prefix: "video"
        'cn' is added before User email prefix to indicate team affiliation (only one 'cn', no fixed suffix).
        
        Important: Title(EN/Shortener) is normalized (spaces replaced with underscores and converted to lowercase).
        
        Args:
            program_code: Program Code (e.g., 'KR000P05S01')
            title_en_shortener: Title(EN/Shortener) (e.g., 'RomanticIsland' or 'Romantic Island')
            creative_type: Creative type (e.g., 'highlight', 'epi', 'teaser') - mapped from frontend values
            number: Number (required when creative_type='highlight' or 'epi')
            intro_ep_no: Intro Ep No (required when creative_type='highlight' or 'epi')
            text_included: Whether text is included
            concept_keyword: Concept keyword (optional)
            language: Language (e.g., 'en', 'kr', 'jp', 'th', 'id')
        
        Returns:
            Generated Ad Name
        """
        parts: List[str] = []
        
        # Fixed prefix
        parts.append("video")
        
        # Program code
        parts.append(program_code)
        
        # Title(EN/Shortener) (normalize: replace spaces with underscores and convert to lowercase)
        parts.append(normalize_for_naming(title_en_shortener))
        
        # Creative type (used as-is: highlight, teaser, epi)
        # Map frontend values to naming values
        creative_type_mapping = {
            "highlight": "highlight",
            "teaser": "teaser",
            "epi": "epi",
        }
        naming_creative_type = creative_type_mapping.get(creative_type.lower(), creative_type.lower())
        parts.append(naming_creative_type)
        
        # Conditional: Number and Intro Ep No (only when creative_type='highlight' or 'epi')
        if creative_type.lower() == "highlight" or creative_type.lower() == "epi":
            if number:
                parts.append(number)
            if intro_ep_no:
                parts.append(intro_ep_no)
        
        # Conditional: Text included
        if text_included:
            parts.append("txt")
        
        # Conditional: concept keyword with "_intro" suffix
        if concept_keyword:
            parts.append(f"{concept_keyword}_intro")
        
        # Language
        parts.append(language)
        
        # Add 'cn' before user email prefix to indicate team affiliation
        parts.append("cn")
        
        # User email prefix (only added if provided)
        if user_email_prefix:
            parts.append(user_email_prefix)
        
        # Note: Only one 'cn' is added (before user email prefix), no fixed suffix 'cn'
        
        return "_".join(parts)
    
    @staticmethod
    def generate_ad_names(
        program_code: str,
        title_en_shortener: str,
        ads: List[dict],
        user_email_prefix: str = "",
    ) -> List[str]:
        """
        Generate multiple Ad Names in batch.
        
        Args:
            program_code: Program Code
            title_en_shortener: Title(EN/Shortener)
            ads: List of ad field dictionaries, each containing:
                - creative_type: str (used as-is, no abbreviation)
                - number: str | None
                - intro_ep_no: str | None
                - text_included: bool
                - concept_keyword: str | None
                - language: str
            user_email_prefix: User email prefix (optional)
        
        Returns:
            List of generated Ad Names (same length as ads input)
        """
        if len(ads) > 30:
            raise ValueError(f"Maximum 30 ads allowed, got {len(ads)}")
        
        ad_names = []
        for ad in ads:
            ad_name = NamingService.generate_ad_name(
                program_code=program_code,
                title_en_shortener=title_en_shortener,
                creative_type=ad["creative_type"],
                number=ad.get("number"),
                intro_ep_no=ad.get("intro_ep_no"),
                text_included=ad.get("text_included", False),
                concept_keyword=ad.get("concept_keyword"),
                language=ad["language"],
                user_email_prefix=user_email_prefix,
            )
            ad_names.append(ad_name)

        return ad_names

    # ============================================================
    # 新命名规则方法 (New Naming Convention Methods)
    # ============================================================

    @staticmethod
    def generate_adset_name_v2(
        country: str,
        language: str,
        media_source: str,
        os: str,
        optimizer: str,
        date: str,
        drama_id: str,
        event: str,
        optional: str | None = None,
    ) -> str:
        """
        Generate Ad Set Name according to new naming rules.

        格式: app-vigloo_{国家}_{语言}_{传媒资源}_{路径类型}_{优化器}_{日期}_{剧集}_{事件}_{其他}
        例子: App-vigloo_us_en_fb_w2a_jade_1000325_purchase_v1

        Args:
            country: Country code (e.g., 'us', 'ww', 'kr')
            language: Language code (e.g., 'en', 'es', 'kr')
            media_source: Media source (e.g., 'fb', 'tt', 'go')
            os: Path type / OS (e.g., 'w2a', 'ios', 'and')
            optimizer: Optimizer name (e.g., 'jade', 'kino', 'silas')
            date: Date in format MMDD or YYMMDD (e.g., '1205', '1000325')
            drama_id: Drama/Program ID (e.g., '10000235')
            event: Event type (e.g., 'purchase', 'install')
            optional: Optional suffix (e.g., 'v1', 'v2')

        Returns:
            Generated Ad Set Name
        """
        parts: List[str] = ["app-vigloo"]

        # Required fields
        parts.append(country.lower())
        parts.append(language.lower())
        parts.append(media_source.lower())
        parts.append(os.lower())
        parts.append(optimizer.lower())
        parts.append(date)
        parts.append(drama_id)
        parts.append(event.lower())

        # Optional suffix
        if optional:
            parts.append(optional.lower())

        return "_".join(parts)

    @staticmethod
    def generate_ad_name_v2(
        drama_id: str,
        language: str,
        team: str,
        designer: str,
        date: str,
        creative_type: str,
        number: str | None = None,
        optional: str | None = None,
    ) -> str:
        """
        Generate Ad Name according to new naming rules.

        格式: {戏剧ID}_{语言}_{团队}_{设计师}_{日期}_{类型}_{数字}_{其他}
        团队: vc (vigloo cn), vk (vigloo kr), cj (代理)
        例子:
        - 10000235_en_vc_eason_1205_hilight_01
        - 10000234_kr_vk_juria_1205_episode_01-05_txt
        - 10000234_kr_cj_juria_1205_episode_01-05_ctn

        Args:
            drama_id: Drama/Program ID (e.g., '10000235')
            language: Language code (e.g., 'en', 'kr', 'jp')
            team: Team code (vc, vk, cj)
            designer: Designer name (e.g., 'eason', 'kyrie', 'beita')
            date: Date in format MMDD (e.g., '1205')
            creative_type: Creative type (e.g., 'hilight', 'episode', 'teaser')
            number: Number or range (e.g., '01', '01-05')
            optional: Optional suffix (e.g., 'txt', 'ctn')

        Returns:
            Generated Ad Name
        """
        parts: List[str] = []

        # Required fields
        parts.append(drama_id)
        parts.append(language.lower())
        parts.append(team.lower())
        parts.append(designer.lower())
        parts.append(date)
        parts.append(creative_type.lower())

        # Optional number
        if number:
            parts.append(number)

        # Optional suffix
        if optional:
            parts.append(optional.lower())

        return "_".join(parts)

    @staticmethod
    def generate_ad_names_v2(ads: List[dict]) -> List[str]:
        """
        Generate multiple Ad Names in batch using new naming rules.

        Args:
            ads: List of ad field dictionaries, each containing:
                - drama_id: str
                - language: str
                - team: str
                - designer: str
                - date: str
                - creative_type: str
                - number: str | None
                - optional: str | None

        Returns:
            List of generated Ad Names (same length as ads input)
        """
        if len(ads) > 30:
            raise ValueError(f"Maximum 30 ads allowed, got {len(ads)}")

        ad_names = []
        for ad in ads:
            ad_name = NamingService.generate_ad_name_v2(
                drama_id=ad["drama_id"],
                language=ad["language"],
                team=ad["team"],
                designer=ad["designer"],
                date=ad["date"],
                creative_type=ad["creative_type"],
                number=ad.get("number"),
                optional=ad.get("optional"),
            )
            ad_names.append(ad_name)

        return ad_names

