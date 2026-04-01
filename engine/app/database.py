from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import AuthenticatedUser
from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def apply_rls_context(session: AsyncSession, user: AuthenticatedUser) -> None:
    claims = {
        "sub": user.user_id,
        "role": user.role,
        "org_id": user.org_id,
        "persona": user.persona,
        "org_type": user.org_type,
        "email": user.email,
    }

    await session.execute(text("select set_config('request.jwt.claims', :claims, true)"), {"claims": str(claims).replace("'", '"')})
    await session.execute(text("select set_config('request.jwt.claim.sub', :sub, true)"), {"sub": user.user_id})
    await session.execute(text("select set_config('request.jwt.claim.role', :role, true)"), {"role": user.role})


async def get_rls_session(user: AuthenticatedUser) -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
      await apply_rls_context(session, user)
      try:
          yield session
      finally:
          await session.close()
