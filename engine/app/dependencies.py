from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_rls_session


async def get_current_session(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AsyncIterator[AsyncSession]:
    async for session in get_rls_session(user):
        yield session
