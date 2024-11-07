import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class JWT:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT token
        
        Args:
            data: Dictionary containing claims to encode in the token
            expires_delta: Optional timedelta for token expiration
            
        Returns:
            Encoded JWT token as string
        """
        # Convert data to dict if it's not already one
        to_encode = {"sub": data} if isinstance(data, (str, int)) else data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)  # Default 15 min
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow()
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and verify a JWT token
        
        Args:
            token: JWT token string to decode
            
        Returns:
            Dictionary containing the decoded claims. If the token was created
            with a string/int value, it will be in the 'sub' key.
            
        Raises:
            jwt.InvalidTokenError: If token is invalid or expired
        """
        decoded = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        return decoded

    def verify_token(self, token: str) -> bool:
        """
        Verify if a token is valid
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Boolean indicating if token is valid
        """
        try:
            self.decode_token(token)
            return True
        except jwt.InvalidTokenError:
            return False
