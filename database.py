import motor.motor_asyncio
from beanie import init_beanie

from config import settings
from models import TamilYogiMovie


async def init():
    # Create Motor client
    client = motor.motor_asyncio.AsyncIOMotorClient(
        settings.mongo_uri
    )

    # Init beanie with the Product document class
    await init_beanie(database=client.streamio, document_models=[TamilYogiMovie])
