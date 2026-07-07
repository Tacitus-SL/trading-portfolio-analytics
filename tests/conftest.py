from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv
import pytest_asyncio
import asyncpg
import os

from main import app

load_dotenv()

TEST_DB_URL = os.getenv("DATABASE_URL")
if not TEST_DB_URL:
    raise ValueError("DATABASE_URL is not set in .env file")


@pytest_asyncio.fixture(scope="session")
async def db_pool():
    pool = await asyncpg.create_pool(TEST_DB_URL)
    yield pool
    await pool.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database(db_pool):
    async with db_pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

        with open("schema.sql", "r", encoding="utf-8") as f:
            schema = f.read()
        await conn.execute(schema)

    yield


@pytest_asyncio.fixture
async def client(db_pool):
    app.state.db_pool = db_pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac