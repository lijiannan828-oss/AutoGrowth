"\"\"\"OAuth related API endpoints.\"\"\""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.schemas.auth import AuthenticatedUser
from app.schemas.oauth import OAuthCodeRequest, OAuthExchangeResponse
from app.services import google_oauth_service

router = APIRouter()


@router.post(
    "/exchange",
    response_model=OAuthExchangeResponse,
    status_code=status.HTTP_200_OK,
    summary="交换授权码并保存刷新令牌",
)
def exchange_code(
    payload: OAuthCodeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> OAuthExchangeResponse:
    """Exchange Google auth code for refresh token and store securely."""
    try:
        token_result = google_oauth_service.exchange_code(
            auth_code=payload.code,
            redirect_uri=payload.redirect_uri,
            scope=payload.scopes,
        )
        token_ref = google_oauth_service.store_refresh_token(current_user, token_result)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return OAuthExchangeResponse(
        token_ref=token_ref,
        expires_in=token_result.expires_in,
        scope=token_result.scope,
        token_type=token_result.token_type,
    )



