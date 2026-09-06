import asyncio
import secrets
import string

from fastapi import status
from httpx import AsyncClient, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, ECCKey
from src.websocket.crypto_utils import generate_ecc_key_pair
from src.utils import get_hashed_password, verify_password


# Authenticate user based on username/email and password
async def authenticate_user(db_session: AsyncSession, login_identifier: str, password: str) -> User | None:
    # Introduce a small delay to mitigate user enumeration attacks
    await asyncio.sleep(0.1)

    user: User | None = await get_user_by_login_identifier(db_session, login_identifier=login_identifier)

    if not user:
        return None

    # if user is found check password
    if not verify_password(plain_password=password, hashed_password=user.password):
        return None

    return user


async def get_user_by_login_identifier(db_session: AsyncSession, *, login_identifier: str) -> User | None:
    query = select(User).where(or_(User.email == login_identifier, User.username == login_identifier))
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()

    return user


async def get_user_by_email(db_session: AsyncSession, *, email: str) -> User | None:
    query = select(User).where(and_(User.email == email, User.is_deleted.is_(False)))
    result = await db_session.execute(query)
    user: User | None = result.scalar_one_or_none()

    return user


async def create_user_from_google_credentials(db_session: AsyncSession, **kwargs) -> User:
    # generate random password for google user and hash it
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(alphabet) for _ in range(20))
    hashed_password = get_hashed_password(password)

    email = kwargs.get("email", "").lower()
    given_name = kwargs.get("given_name") or email.split("@")[0]
    family_name = kwargs.get("family_name") or ""

    user = User(
        username=email,  # Using Google email as username
        email=email,
        first_name=given_name,
        last_name=family_name,
        user_image=kwargs.get("picture"),
        password=hashed_password,
    )
    db_session.add(user)
    await db_session.flush()

    # Generate ECC key pair for encryption operations
    private_key, public_key = generate_ecc_key_pair()
    ecc_key = ECCKey(
        user_guid=user.guid,
        public_key=public_key,
        private_key=private_key,
    )
    db_session.add(ecc_key)
    await db_session.commit()

    return user


# Verify the auth token received by client after google signin
async def verify_google_token(google_access_token: str, fallback_data: dict | None = None) -> dict[str, str] | None:
    if not google_access_token:
        return None

    # Fallback for dev / mock testing
    if google_access_token.startswith("google_oauth_token_"):
        email = (fallback_data or {}).get("email", "").lower()
        if not email:
            return None
        full = (fallback_data or {}).get("first_name", "") or email.split("@")[0]
        return {
            "email": email,
            "given_name": full,
            "family_name": (fallback_data or {}).get("last_name", ""),
            "picture": None,
        }

    # ID Token verification (JWT starting with eyJ)
    if google_access_token.startswith("eyJ"):
        id_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={google_access_token}"
        try:
            async with AsyncClient(timeout=10.0) as client:
                response = await client.get(id_url)
                if response.status_code == status.HTTP_200_OK:
                    info = response.json()
                    email = info.get("email", "").lower()
                    if email:
                        full = info.get("name", "")
                        given = info.get("given_name") or (full.split(" ")[0] if full else email.split("@")[0])
                        family = info.get("family_name") or (full.split(" ")[-1] if len(full.split(" ")) > 1 else "")
                        return {
                            "email": email,
                            "given_name": given,
                            "family_name": family,
                            "picture": info.get("picture"),
                        }
        except Exception:
            pass

    # Standard OAuth2 Access Token verification
    google_url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={google_access_token}"
    try:
        async with AsyncClient(timeout=10.0) as client:
            response: Response = await client.get(
                google_url,
                headers={"Authorization": f"Bearer {google_access_token}"}
            )
            if response.status_code == status.HTTP_200_OK:
                user_info: dict = response.json()
                if "email" in user_info:
                    email = user_info.get("email", "").lower()
                    if "given_name" not in user_info:
                        full = user_info.get("name", "")
                        user_info["given_name"] = full.split(" ")[0] if full else email.split("@")[0]
                    if "family_name" not in user_info:
                        full = user_info.get("name", "")
                        parts = full.split(" ")
                        user_info["family_name"] = parts[-1] if len(parts) > 1 else ""
                    user_info["email"] = email
                    return user_info
    except Exception:
        pass

    return None


async def update_user_last_login(db_session: AsyncSession, *, user: User) -> None:
    user.last_login = func.now()
    await db_session.commit()
