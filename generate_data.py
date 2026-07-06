from psycopg2.extras import execute_values
from faker import Faker
import psycopg2
import random

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set in .env file")

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

stocks_list = [
    {"ticker": "AAPL", "name": "Apple Inc."},
    {"ticker": "TSLA", "name": "Tesla, Inc."},
    {"ticker": "NVDA", "name": "NVIDIA Corporation"},
    {"ticker": "MSFT", "name": "Microsoft Corporation"},
    {"ticker": "AMZN", "name": "Amazon.com, Inc."},
    {"ticker": "GOOGL", "name": "Alphabet Inc."},
    {"ticker": "META", "name": "Meta Platforms, Inc."},
    {"ticker": "NFLX", "name": "Netflix, Inc."},
    {"ticker": "AMD", "name": "Advanced Micro Devices, Inc."},
    {"ticker": "INTC", "name": "Intel Corporation"},
    {"ticker": "BABA", "name": "Alibaba Group Holding Limited"},
    {"ticker": "PYPL", "name": "PayPal Holdings, Inc."},
    {"ticker": "V", "name": "Visa Inc."},
    {"ticker": "MA", "name": "Mastercard Incorporated"},
    {"ticker": "DIS", "name": "The Walt Disney Company"}
]

def insert_stocks(stocks ):
    query = """
        INSERT INTO stocks (ticker, company_name)
        VALUES (%s, %s)
        ON CONFLICT (ticker) DO NOTHING;   
    """

    values_to_insert = [(stock["ticker"], stock["name"]) for stock in stocks]

    cur.executemany(query, values_to_insert)
    print(f"Succesfully added {len(stocks)} stocks.")


def insert_fake_users(count=1000):
    fake = Faker()

    query = """
        INSERT INTO users (name, email)
        VALUES (%s, %s)
        ON CONFLICT (email) DO NOTHING;
    """

    users_data = []
    for i in range(count):
        name = fake.name()
        email = fake.unique.email()
        users_data.append((name, email))

    cur.executemany(query, users_data)
    print(f"Succesfully added {count} users.")

def get_ids_from_table(table_name):
    cur.execute(f"SELECT id FROM {table_name};")

    rows = cur.fetchall()

    ids_list = [row[0] for row in rows]
    return ids_list

def insert_transactions(batch_size=10000, count=1000000):
    fake = Faker()

    user_ids = get_ids_from_table("users")
    stock_ids = get_ids_from_table("stocks")

    if not user_ids or not stock_ids:
        print("ERROR: Create users and stocks first!")
        return

    query = """
        INSERT INTO transactions (user_id, stock_id, transaction_type, quantity, price, executed_at)
        VALUES %s;
    """

    batch = []
    inserted_total = 0

    for i in range(count):
        user_id = random.choice(user_ids)
        stock_id = random.choice(stock_ids)
        transaction_type = fake.random_element(elements=['BUY', 'SELL'])
        quantity = random.randint(1, 100)
        price = round(random.uniform(10.0, 5000.0), 2)
        executed_at = fake.date_time_between(start_date='-2y', end_date='now')

        row = (user_id, stock_id, transaction_type, quantity, price, executed_at)
        batch.append(row)

        if len(batch) == batch_size:
            execute_values(cur, query, batch)
            inserted_total += len(batch)
            print(f"Inserted transactions: {inserted_total}/{count}")
            batch = []

    if batch:
        execute_values(cur, query, batch)
        inserted_total += len(batch)
        print(f"Inserted transactions: {inserted_total}/{count}")

if __name__ == "__main__":
    try:
        conn.autocommit = False
        insert_stocks(stocks_list)
        insert_fake_users(1000)

        insert_transactions(batch_size=10000, count=1000000)

        conn.commit()
        print("Data successfully commited.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
        print("Connection is closed.")