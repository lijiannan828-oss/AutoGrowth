"""OneLink URL generation service according to SOP rules."""

from typing import List
from urllib.parse import urlencode, quote

from app.utils.mappings import get_media_source_pid


class OneLinkService:
    """Service for generating OneLink URLs according to SOP rules."""
    
    BASE_URL = "https://vigloo.onelink.me/SrIM"
    
    @staticmethod
    def generate_onelink_url(
        base_url: str,
        media_source: str,
        campaign_name: str,
        adset_name: str,
        ad_name: str,
        program_id: str,
        season_id: str,
        episode_number: str,
        onelink_language: str,  # Onelink Language (e.g., 'en', 'ko', 'ja', 'id', 'zh')
        fixed_params: dict | None = None,
    ) -> str:
        """
        Generate a single OneLink URL according to SOP rules.
        
        Args:
            base_url: Base OneLink URL (default: "https://vigloo.onelink.me/SrIM")
            media_source: Media source (e.g., 'fb', 'tt', 'go')
            campaign_name: Generated Campaign Name
            adset_name: Generated Ad Set Name
            ad_name: Generated Ad Name for this specific Ad
            program_id: Program ID from Program Info (specifically from Google Sheets "All" sheet's "id" field)
            season_id: Season ID from Program Info (specifically from Google Sheets "All" sheet's "seasonId" field, if exists)
            episode_number: Episode Number from Ad form (Onelink Intro Ep No, required, default "1")
            onelink_language: Onelink Language from Ad form (e.g., 'en', 'ko', 'ja', 'id', 'zh')
            fixed_params: Additional fixed parameters from Program Info (optional)
        
        Returns:
            Complete OneLink URL with all parameters
        """
        # Get PID from media source mapping
        pid = get_media_source_pid(media_source)
        
        # Build parameters dictionary
        params: dict[str, str] = {}
        
        # Core attribution parameters
        params["pid"] = pid
        params["c"] = campaign_name  # URLSearchParams will auto-encode
        params["af_adset"] = adset_name
        params["af_ad"] = ad_name
        
        # Program parameters
        params["programId"] = program_id
        params["seasonId"] = season_id
        
        # Deep link parameters
        # deep_link_sub1 appears twice (as per SOP)
        params["deep_link_sub1"] = program_id  # First occurrence
        params["deep_link_sub2"] = season_id
        params["deep_link_sub3"] = episode_number
        
        # Web-to-App fallback URL (af_web_dp)
        # Format: https://www.vigloo.com/{onelink_language}/video/{programId}?episode={episodeNumber}
        # Use onelink_language (mapped: en, ko, ja, id, zh)
        web_fallback_url = f"https://www.vigloo.com/{onelink_language}/video/{program_id}?episode={episode_number}"
        params["af_web_dp"] = web_fallback_url
        
        # Deep link configuration
        params["af_force_deeplink"] = "true"
        params["is_retargeting"] = "true"
        
        # App deep link URI (af_dp) - overall encoded
        # Format: vigloo://deeplink/program?programId={programId}&seasonId={seasonId}&episodeNumber={episodeNumber}
        # The entire URI string is URL encoded
        # Note: We encode it here, but it will be encoded again when building the query string
        # So we need to store the encoded value directly
        deep_link_uri = f"vigloo://deeplink/program?programId={program_id}&seasonId={season_id}&episodeNumber={episode_number}"
        # Store the encoded value (will be used directly in query string without re-encoding)
        params["af_dp"] = quote(deep_link_uri, safe="")
        
        # Attribution window parameters
        params["af_reengagement_window"] = "7d"
        params["af_inactivity_window"] = "7d"
        params["af_click_lookback"] = "7d"
        
        # Deep link context
        params["deep_link_value"] = "program"
        
        # Add fixed parameters if provided
        if fixed_params:
            for key, value in fixed_params.items():
                if key not in params:  # Don't override existing params
                    params[key] = str(value)
        
        # Build URL with parameters
        # Handle deep_link_sub1 duplication by manually building query string
        query_parts: List[str] = []
        for key, value in params.items():
            encoded_key = quote(str(key), safe="")
            # af_dp is already encoded, so don't encode it again
            if key == "af_dp":
                encoded_value = str(value)  # Already encoded
            else:
                encoded_value = quote(str(value), safe="")
            query_parts.append(f"{encoded_key}={encoded_value}")
        
        # Add deep_link_sub1 again (second occurrence, as per SOP)
        encoded_program_id = quote(program_id, safe="")
        query_parts.append(f"deep_link_sub1={encoded_program_id}")
        
        query_string = "&".join(query_parts)
        full_url = f"{base_url}?{query_string}"
        
        return full_url
    
    @staticmethod
    def generate_onelink_urls(
        base_url: str,
        media_source: str,
        campaign_name: str,
        adset_name: str,
        ad_names: List[str],
        program_id: str,
        season_id: str,
            ads: List[dict],
        fixed_params: dict | None = None,
    ) -> List[str]:
        """
        Generate multiple OneLink URLs in batch.
        
        Args:
            base_url: Base OneLink URL
            media_source: Media source
            campaign_name: Generated Campaign Name
            adset_name: Generated Ad Set Name
            ad_names: List of generated Ad Names (same length as ads)
            program_id: Program ID from Program Info (specifically from Google Sheets "All" sheet's "id" field)
            season_id: Season ID from Program Info (specifically from Google Sheets "All" sheet's "seasonId" field, if exists)
            ads: List of ad field dictionaries, each containing:
                - language: str
                - onelinkIntroEpNo: str (Onelink Intro Ep No, used for deep_link_sub3 and af_dp/af_web_dp, required, default "1")
            fixed_params: Additional fixed parameters from Program Info (optional)
        
        Returns:
            List of generated OneLink URLs (same length as ads input)
        
        Raises:
            ValueError: If ad_names and ads lengths don't match, or if more than 30 ads
        """
        if len(ad_names) != len(ads):
            raise ValueError(
                f"Ad names count ({len(ad_names)}) must match ads count ({len(ads)})"
            )
        
        if len(ads) > 30:
            raise ValueError(f"Maximum 30 ads allowed, got {len(ads)}")
        
        onelink_urls = []
        for i, (ad_name, ad) in enumerate(zip(ad_names, ads)):
            # Get episode number from ad (Onelink Intro Ep No, required, default "1")
            episode_number = ad.get("onelinkIntroEpNo") or ad.get("introEpNo") or "1"
            onelink_language = ad.get("onelinkLanguage") or ad.get("language") or "en"
            
            if not onelink_language or onelink_language.strip() == "":
                raise ValueError(f"Ad {i + 1} missing required 'onelinkLanguage' field")
            
            if not episode_number or episode_number.strip() == "":
                raise ValueError(f"Ad {i + 1} missing required 'onelinkIntroEpNo' field")
            
            onelink_url = OneLinkService.generate_onelink_url(
                base_url=base_url,
                media_source=media_source,
                campaign_name=campaign_name,
                adset_name=adset_name,
                ad_name=ad_name,
                program_id=program_id,
                season_id=season_id,
                episode_number=episode_number,
                onelink_language=onelink_language,
                fixed_params=fixed_params,
            )
            onelink_urls.append(onelink_url)
        
        return onelink_urls

