"\"\"\"OAuth related schemas.\"\"\""

from typing import List, Optional

from pydantic import BaseModel, Field


class OAuthCodeRequest(BaseModel):
    code: str = Field(..., description="Google 返回的授权码")
    redirect_uri: Optional[str] = Field(default=None, description="授权时使用的 redirect URI")
    scopes: Optional[List[str]] = Field(default=None, description="客户端声明的授权范围")


class OAuthExchangeResponse(BaseModel):
    token_ref: str = Field(..., description="后端存储的 token 引用 ID")
    expires_in: Optional[int] = Field(None, description="Access token 过期时间，秒")
    scope: List[str] = Field(default_factory=list, description="最终授权范围")
    token_type: Optional[str] = Field(None, description="Access token 类型")



