import asyncio
import logging
from prisma import Prisma

logger = logging.getLogger(__name__)

prisma = Prisma()

_MAX_CONNECT_RETRIES = 3
_RETRY_DELAY_SECONDS = 2.0

async def connect_db() -> None:
    if prisma.is_connected():
        logger.debug("Prisma client already connected")
        return

    last_exc = None
    for attempt in range(1, _MAX_CONNECT_RETRIES + 1):
        try:
            await prisma.connect()
            logger.info("Prisma client connected to database")
            return
        except Exception as e:
            last_exc = e
            if attempt < _MAX_CONNECT_RETRIES:
                delay = _RETRY_DELAY_SECONDS * attempt
                logger.warning(
                    "DB connect attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt, _MAX_CONNECT_RETRIES, e, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.error("Failed to connect Prisma client after %d attempts: %s", _MAX_CONNECT_RETRIES, e)
    
    raise RuntimeError(f"Could not connect to database after {_MAX_CONNECT_RETRIES} attempts") from last_exc

async def disconnect_db() -> None:
    if not prisma.is_connected():
        logger.debug("Prisma client already disconnected")
        return
    try:
        await prisma.disconnect()
        logger.info("Prisma client disconnected from database")
    except Exception as e:
        logger.error("Error disconnecting Prisma client: %s", e)
        raise
