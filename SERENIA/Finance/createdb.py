import sqlite3

try:
    conn = sqlite3.connect("data.db")
    print("Connected to SQLite")

    db = conn.cursor()
    db.execute("""
    CREATE TABLE accounts (
        id INTEGER,
        name TEXT,
        type TEXT,
        subtype TEXT,
        balance REAL,
        persons_id INTEGER,
        dependency INTEGEER,
        deleted INTEGER,
        PRIMARY KEY(id),
        FOREIGN KEY(persons_id) REFERENCES persons(id)
    )
    """)
    db.execute("""
    CREATE TABLE transactions (
        id INTEGER,
        persons_id INTEGER,
        debit_id INTEGER,
        credit_id INTEGER,
        particular TEXT,
        amount REAL,
        date INTEGER,
        PRIMARY KEY(id),
        FOREIGN KEY(persons_id) REFERENCES persons(id),
        FOREIGN KEY(debit_id) REFERENCES accounts(id),
        FOREIGN KEY(credit_id) REFERENCES accounts(id)
    )
    """)
    db.execute("CREATE INDEX accounts_id_index ON accounts(id)")
    db.execute("""
    CREATE TABLE persons (
        id INTEGER,
        name TEXT,
        password TEXT,
        date INTEGER,
        currency TEXT,
        PRIMARY KEY(id)
    )
    """)
    db.execute("CREATE INDEX persons_id_index ON persons(id)")
    db.execute("CREATE INDEX name_index ON persons(name)")

    conn.commit()

except sqlite3.Error as e:
    print("Failed to open database:", e)

finally:
    if conn:
        conn.close()
        print("The SQLite connection is closed")

