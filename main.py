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


@app.get("/analytics/growth")
async def get_mom_growth():
    query = """
        WITH monthly_volumes AS (
            SELECT
                DATE_TRUNC('month', executed_at) AS trade_month,
                SUM(quantity * price) AS current_volume
            FROM transactions
            GROUP BY trade_month
        ),
        volumes_with_lag AS (
            SELECT
                trade_month,
                current_volume,
                LAG(current_volume) OVER (ORDER BY trade_month) AS previous_volume
            FROM monthly_volumes
        )
        SELECT
            trade_month,
            current_volume,
            previous_volume,
            ROUND(((current_volume - previous_volume) / NULLIF(previous_volume, 0)) * 100, 2) AS growth_percentage
        FROM volumes_with_lag
        ORDER BY trade_month DESC;
    """
    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(query)

    return [dict(row) for row in rows]


@app.get("/analytics/whales")
async def get_whales():
    query = """
        WITH user_volumes AS (
            SELECT
                user_id,
                SUM(quantity * price) AS total_volume
            FROM transactions
            GROUP BY user_id
        ),
        user_percentiles AS (
            SELECT
                user_id,
                total_volume,
                NTILE(100) OVER (ORDER BY total_volume DESC) AS percentile_group
            FROM user_volumes
        )
        SELECT
            p.user_id,
            u.name AS user_name,
            p.total_volume,
            p.percentile_group
        FROM user_percentiles AS p
        JOIN users AS u ON u.id = p.user_id
        WHERE percentile_group = 1
        ORDER BY p.total_volume DESC;
    """
    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(query)

    return [dict(row) for row in rows]


@app.get("/portfolio/{user_id}/summary")
async def get_portfolio_summary(user_id: int):
    query = """
        SELECT
            s.company_name,
            SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.quantity ELSE -t.quantity END) AS stock_balance
        FROM transactions AS t
        LEFT JOIN stocks AS s ON s.id = t.stock_id
        WHERE t.user_id = $1
        GROUP BY ROLLUP(s.company_name)
        ORDER BY (s.company_name IS NULL) ASC, s.company_name ASC;
    """
    async with app.state.db_pool.acquire() as conn:
        rows = await conn.fetch(query, user_id)

    if not rows:
        raise HTTPException(status_code=404, detail="Portfolio not found or empty")

    result = []
    for row in rows:
        row_dict = dict(row)
        if row_dict['company_name'] is None:
            row_dict['company_name'] = "TOTAL"
        result.append(row_dict)

    return result