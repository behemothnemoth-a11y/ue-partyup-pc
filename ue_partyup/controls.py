"""Read-probed settings adapter selection."""
from contextlib import asynccontextmanager
from .session import Session, NoReply


@asynccontextmanager
async def settings_session(speaker, experimental=False):
    if speaker.experimental and not experimental:
        raise ValueError('Enable experimental compatibility for this speaker.')
    modern = Session(speaker)
    try:
        await modern.connect()
    except NoReply:
        if not speaker.experimental:
            raise
    else:
        from .settings import Settings
        try:
            yield Settings(modern)
        finally:
            modern.close()
        return
    from .legacy import LegacySession, LegacySettings
    async with LegacySession(speaker, experimental=experimental) as session:
        probe = await session.probe()
        if not probe.broadcast_available or probe.profile == 'NO_GROUP':
            raise RuntimeError('No known legacy PartyUp profile was confirmed.')
        yield LegacySettings(session)
