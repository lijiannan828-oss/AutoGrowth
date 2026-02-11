"""Mapping utilities for naming generation."""

# 投手列表 (Optimizer)
OPTIMIZERS: list[str] = [
    "silas",
    "kimi",
    "kino",
    "zane",
    "hannibal",
    "juria",
    "jade",
    "lyla",
    "joy",
]

# 设计师列表 (Designer)
DESIGNERS: list[str] = [
    "eason",
    "kyrie",
    "beita",
    "maggie",
    "helen",
]

# 团队映射 (Team)
# vc: vigloo cn, vk: vigloo kr, cj: 代理
TEAMS: dict[str, str] = {
    "vc": "vigloo cn",
    "vk": "vigloo kr",
    "cj": "代理",
}

# Optimization types to abbreviation mapping
# install -> [i], others -> [e]
OPTIMIZATION_ABBREVIATION_MAP: dict[str, str] = {
    "install": "i",
    "watch": "e",
    "purchase": "e",
    "subscription": "e",
}

# Optimization types to naming format mapping
# subscription -> subs in naming
OPTIMIZATION_NAMING_MAP: dict[str, str] = {
    "install": "install",
    "watch": "watch",
    "purchase": "purchase",
    "subscription": "subs",
}

# Media source to PID mapping
MEDIA_SOURCE_PID_MAP: dict[str, str] = {
    "fb": "metaweb_int",  # Facebook (Meta, Instagram)
    "tt": "tiktok_int",   # TikTok
    "go": "google_int",   # Google
    "sc": "snapchat_int", # Snapchat
    "pg": "pangle_int", # Pangle
}


def get_optimization_abbreviation(optimization_type: str) -> str:
    """
    Get optimization abbreviation from optimization type.
    
    Rules:
    - install -> [i]
    - others -> [e]
    
    Args:
        optimization_type: Optimization type (e.g., 'install', 'watch', 'purchase', 'subscription')
    
    Returns:
        Abbreviation ('i' for install, 'e' for others)
    
    Raises:
        ValueError: If optimization_type is not found in mapping
    """
    if not optimization_type:
        raise ValueError("Optimization type cannot be empty")
    
    abbreviation = OPTIMIZATION_ABBREVIATION_MAP.get(optimization_type.lower())
    if abbreviation is None:
        raise ValueError(
            f"Unknown optimization type: {optimization_type}. "
            f"Supported types: {list(OPTIMIZATION_ABBREVIATION_MAP.keys())}"
        )
    
    return abbreviation


def get_optimization_naming(optimization_type: str) -> str:
    """
    Get optimization naming format from optimization type.
    
    Rules:
    - subscription -> subs
    - others -> as-is
    
    Args:
        optimization_type: Optimization type (e.g., 'install', 'watch', 'purchase', 'subscription')
    
    Returns:
        Naming format (e.g., 'install', 'watch', 'purchase', 'subs')
    
    Raises:
        ValueError: If optimization_type is not found in mapping
    """
    if not optimization_type:
        raise ValueError("Optimization type cannot be empty")
    
    naming = OPTIMIZATION_NAMING_MAP.get(optimization_type.lower())
    if naming is None:
        raise ValueError(
            f"Unknown optimization type: {optimization_type}. "
            f"Supported types: {list(OPTIMIZATION_NAMING_MAP.keys())}"
        )
    
    return naming


def get_media_source_pid(media_source: str) -> str:
    """
    Get PID from media source.
    
    Args:
        media_source: Media source (e.g., 'fb', 'tt', 'go')
    
    Returns:
        PID value (e.g., 'metaweb_int', 'tiktok_int', 'google_int')
    
    Raises:
        ValueError: If media_source is not found in mapping
    """
    if not media_source:
        raise ValueError("Media source cannot be empty")
    
    pid = MEDIA_SOURCE_PID_MAP.get(media_source.lower())
    if pid is None:
        raise ValueError(
            f"Unknown media source: {media_source}. "
            f"Supported sources: {list(MEDIA_SOURCE_PID_MAP.keys())}"
        )
    
    return pid

