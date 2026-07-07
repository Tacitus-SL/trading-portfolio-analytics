import asyncpg
import pytest

pytestmark = pytest.mark.asyncio


async def test_leaderboard_ranking(client, db_pool):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (id, name, email) VALUES (1, 'Elon', 'elon@x.com'), (2, 'Zuck', 'zuck@meta.com');")
        await conn.execute("INSERT INTO stocks (id, ticker, company_name) VALUES (1, 'TSLA', 'Tesla');")

        await conn.execute(
            "INSERT INTO transactions (user_id, stock_id, transaction_type, quantity, price) VALUES (1, 1, 'BUY', 100, 100.00);")
        await conn.execute(
            "INSERT INTO transactions (user_id, stock_id, transaction_type, quantity, price) VALUES (2, 1, 'SELL', 10, 50.00);")

    response = await client.get("/analytics/leaderboard?limit=10")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert data[0]["user_name"] == "Elon"
    assert data[0]["rank"] == 1
    assert data[0]["total_volume"] == 10000.0

    assert data[1]["user_name"] == "Zuck"
    assert data[1]["rank"] == 2
    assert data[1]["total_volume"] == 500.0


async def test_database_rejects_negative_price(db_pool):
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO users (id, name, email) VALUES (1, 'Hacker', 'hack@mail.com');")
        await conn.execute("INSERT INTO stocks (id, ticker, company_name) VALUES (1, 'AAPL', 'Apple');")

        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute("""
                INSERT INTO transactions (user_id, stock_id, transaction_type, quantity, price) 
                VALUES (1, 1, 'BUY', 10, -500.00);
            """)

        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute("""
                INSERT INTO fiat_transactions (user_id, action_type, amount) 
                VALUES (1, 'DEPOSIT', -1000.00);
            """)


async def test_fiat_balance_calculation(client, db_pool):
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO users (id, name, email) VALUES (1, 'Trader', 'trade@mail.com');")
        await conn.execute("INSERT INTO stocks (id, ticker, company_name) VALUES (1, 'NVDA', 'Nvidia');")

        await conn.execute("INSERT INTO fiat_transactions (user_id, action_type, amount) VALUES (1, 'DEPOSIT', 10000);")
        await conn.execute(
            "INSERT INTO fiat_transactions (user_id, action_type, amount) VALUES (1, 'WITHDRAWAL', 2000);")
        await conn.execute(
            "INSERT INTO transactions (user_id, stock_id, transaction_type, quantity, price) VALUES (1, 1, 'BUY', 10, 300);")

    response = await client.get("/portfolio/1/balance")

    assert response.status_code == 200
    data = response.json()
    assert data["total_fiat_balance"] == 5000.0