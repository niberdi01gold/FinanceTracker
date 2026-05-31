import sqlite3
from datetime import datetime

DB_NAME = "financetracker.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            btc_cantidad REAL,
            btc_valor_usd REAL,
            eth_cantidad REAL,
            eth_valor_usd REAL,
            total_usd REAL
        )
    ''')
    conn.commit()
    conn.close()

def guardar_snapshot(btc_cantidad, btc_valor, eth_cantidad, eth_valor, total):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO snapshots (fecha, btc_cantidad, btc_valor_usd, eth_cantidad, eth_valor_usd, total_usd)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M"), btc_cantidad, btc_valor, eth_cantidad, eth_valor, total))
    conn.commit()
    conn.close()

def obtener_snapshot_ayer():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT * FROM snapshots
        ORDER BY id DESC LIMIT 2
    ''')
    rows = c.fetchall()
    conn.close()
    if len(rows) >= 2:
        return rows[1]
    return None

def obtener_snapshot_semana():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT * FROM snapshots
        ORDER BY id ASC LIMIT 1
    ''')
    row = c.fetchone()
    conn.close()
    return row