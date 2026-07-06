# Trading Portfolio Analytics Engine

An asynchronous, high-performance API for analyzing user trading portfolios and stock market data. Designed to handle large datasets (1,000,000+ transactions) with optimized database architecture.

## Tech Stack
* **Language:** Python 3.10+
* **Framework:** FastAPI
* **Database:** PostgreSQL
* **Driver:** `asyncpg` (Asynchronous connection pooling)
* **Data Generation:** `Faker`, `psycopg2` (Batch inserts via `execute_values`)

## Key Features
1. **Highload Data Simulation:** Custom Python script generating 1M+ realistic trading transactions and inserting them via batching in under 20 seconds.
2. **Advanced SQL Analytics:** All heavy calculations (Window functions, moving averages, aggregations) are processed purely on the database level, preventing Python RAM overload.
3. **Optimized DB Architecture:** Proper use of `NUMERIC` types for financial data, Foreign Key constraints (`ON DELETE CASCADE`), and B-Tree indexes.
4. **Async API:** Non-blocking FastAPI server using connection pooling (`asyncpg`) to handle multiple concurrent requests efficiently.

## Database Optimization
During development, analyzing queries with `EXPLAIN ANALYZE` revealed a performance bottleneck. 
Fetching a user's portfolio took **~146ms** due to a *Sequential Scan* across 1,000,000 rows. 

By implementing **B-Tree indexes** on the `user_id` and `stock_id` columns, the query execution time was reduced to **0.5ms** (a ~300x performance increase), switching the execution plan to an *Index Scan*.

## Core SQL Queries

**1. Stock Moving Average (Window Functions)**
Calculates the moving average price for a stock based on the last 10 trades to smooth out price volatility.
```sql
SELECT executed_at, transaction_type, quantity, price,
       AVG(price) OVER (
           ORDER BY executed_at
           ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
       ) AS avg_price_last_10
FROM transactions
WHERE stock_id = $1;
```
**2. Leaderboard**
Ranks users by their total trading volume using DENSE_RANK().
```sql
SELECT DENSE_RANK() OVER (ORDER BY SUM(t.price * t.quantity) DESC) AS rank,
       u.name AS user_name,
       SUM(t.price * t.quantity) AS total_volume
FROM transactions t
JOIN users u on t.user_id = u.id
GROUP BY u.id, u.name
ORDER BY total_volume DESC
LIMIT $1;
```

## How to Run Locally
**1. Clone and install dependencies:**
```bash
pip install -r requirements.txt
```
**2. Setup Database:**
* Create a PostgreSQL database.
* Run the SQL commands from schema.sql to create tables and indexes.
* Create a .env file in the root directory and add your connection string:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

**3. Generate 1,000,000 records:**
```bash
python generate_data.py
```

**4.Start the API server:**
```bash
uvicorn main:app --reload
```

**5. Open Swagger UI:**
Navigate to `http://localhost:8000/docs` in your browser.