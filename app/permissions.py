import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.settings import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(
    token: str = Depends(oauth2_scheme)
):
    print("gelen token",token)
    try:
        response = httpx.get(
            f"{settings.MAIN_BACKEND_URL}/admin/user/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        print("gelen response",response.json())
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not connect to authentication service",
        ) from e
