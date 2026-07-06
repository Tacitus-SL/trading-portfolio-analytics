from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncpg
import os

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set in .env file")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await asyncpg.create_pool(DB_URL, min_size=5, max_size=20)
    print("Database pool created!")
    yield
    await app.state.db_pool.close()
    print("Database pool closed!")


app = FastAPI(lifespan=lifespan, title="Trading Analytics API")

@app.get("/portfolio/{user_id}")
async def get_portfolio(user_id: int):
    query = """
        SELECT s.ticker, s.company_name,
            SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END) AS stock_balance
        FROM transactions t
        JOIN stocks s on t.stock_id = s.id
        WHERE t.user_id = $1
        GROUP BY s.ticker, s.company_name
        HAVING SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END) > 0;
    """
    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(query, user_id)

    if not rows:
        raise HTTPException(status_code=404, detail="Portfolio not found or empty")

    return [dict(row) for row in rows]


@app.get("/analytics/stock/{stock_id}/moving-average")
async def get_moving_average(stock_id: int, limit: int = 50):
    query = """
        SELECT executed_at, transaction_type, quantity, price,
               AVG(price) OVER (
                   ORDER BY executed_at
                   ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
               ) AS avg_price_last_10
        FROM transactions
        WHERE stock_id = $1
        ORDER BY executed_at DESC
        LIMIT $2;
    """
    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(query, stock_id, limit)

    return [dict(row) for row in rows]


@app.get("/analytics/leaderboard")
async def get_leaderboard(limit: int = 10):
    query = """
        SELECT
            DENSE_RANK() OVER (ORDER BY SUM(t.price * t.quantity) DESC) AS rank,
            u.id AS user_id,
            u.name AS user_name,
            SUM(t.price * t.quantity) AS total_volume
        FROM transactions AS t
        JOIN users AS u on t.user_id = u.id
        GROUP BY u.id, u.name
        ORDER BY total_volume DESC
        LIMIT $1;
    """




    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(query, limit)

    return [dict(row) for row in rows]