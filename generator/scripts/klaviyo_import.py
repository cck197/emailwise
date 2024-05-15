from dotenv import load_dotenv

load_dotenv("../../.env")

from generator.db import get_db
from generator.klaviyo import db_import_from_klaviyo, klaviyo_import_from_db


async def import_from_db(**kwargs):
    db = await get_db()
    return await klaviyo_import_from_db(db, **kwargs)


async def db_import(shop):
    db = await get_db()
    return await db_import_from_klaviyo(db, shop)
