"""
Security utilities: Password hashing, JWT tokens, encryption
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
from .config import get_settings

# Password hashing context using bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor of 12 (secure against brute force)
)


class SecurityConfig:
    """Security and authentication configuration"""

    def __init__(self):
        self.settings = get_settings()

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt with salt.
        
        Args:
            password: Plain-text password
            
        Returns:
            Hashed password safe for storage
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify plain password against hashed password.
        
        Args:
            plain_password: Plain-text password from user
            hashed_password: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT access token with claims.
        
        Args:
            data: Claims to include (user_id, username, role, etc.)
            expires_delta: Custom expire time, defaults to ACCESS_TOKEN_EXPIRE_MINUTES
            
        Returns:
            Signed JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.SECRET_KEY,
            algorithm=self.settings.ALGORITHM,
        )
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create JWT refresh token (longer expiry).
        
        Args:
            data: Claims to include
            
        Returns:
            Signed refresh JWT token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.SECRET_KEY,
            algorithm=self.settings.ALGORITHM,
        )
        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token claims
            
        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.SECRET_KEY,
                algorithms=[self.settings.ALGORITHM],
            )
            return payload
        except JWTError as e:
            raise JWTError(f"Invalid token: {str(e)}")

    def generate_random_token(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        Used for password reset, email verification, etc.
        
        Args:
            length: Token length in hex characters (bytes * 2)
            
        Returns:
            Random token
        """
        return secrets.token_hex(length // 2)


# Global security instance
def get_password_hash(password: str) -> str:
    """Convenience function for password hashing"""
    sec = SecurityConfig()
    return sec.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Convenience function for password verification"""
    sec = SecurityConfig()
    return sec.verify_password(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any]) -> str:
    """Convenience function for creating access tokens"""
    sec = SecurityConfig()
    return sec.create_access_token(data)


def verify_token(token: str) -> Dict[str, Any]:
    """Convenience function for verifying tokens"""
    sec = SecurityConfig()
    return sec.verify_token(token)
