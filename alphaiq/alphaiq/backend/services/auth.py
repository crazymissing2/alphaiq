"""
AlphaIQ Auth Service — registration, login, JWT tokens
"""

import hashlib, secrets, uuid, logging
from datetime import datetime, timedelta
from typing import Optional, Dict

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

log = logging.getLogger("auth")
security = HTTPBearer(auto_error=False)

# Simple token store (replace with Redis in production)
_tokens: Dict[str, str] = {}   # token → user_id


class AuthService:
    def __init__(self, db):
        self.db = db

    def _hash_password(self, password: str) -> str:
        salt = "alphaiq_salt_2024"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def create_token(self, user_id: str) -> str:
        token = secrets.token_hex(32)
        _tokens[token] = user_id
        return token

    def get_user_id_from_token(self, token: str) -> Optional[str]:
        return _tokens.get(token)

    async def register(self, username: str, email: str, password: str) -> Optional[Dict]:
        user_id = str(uuid.uuid4())
        pw_hash = self._hash_password(password)
        return await self.db.create_user(user_id, username, email, pw_hash)

    async def authenticate(self, email: str, password: str) -> Optional[Dict]:
        user = await self.db.get_user_by_email(email)
        if not user:
            return None
        if user["password_hash"] != self._hash_password(password):
            return None
        return user

    async def get_current_user(
        self,
        creds: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict:
        if not creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        user_id = self.get_user_id_from_token(creds.credentials)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user = await self.db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
