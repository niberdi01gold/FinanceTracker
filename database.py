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
    c.execute('''
        CREATE TABLE IF NOT EXISTS dividendos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            ticker TEXT,
            monto REAL,
            descripcion TEXT
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
    c.execute('SELECT * FROM snapshots ORDER BY id DESC LIMIT 2')
    rows = c.fetchall()
    conn.close()
    if len(rows) >= 2:
        return rows[1]
    return None

def obtener_snapshot_semana():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM snapshots ORDER BY id ASC LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row

def obtener_rendimiento():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM snapshots ORDER BY id ASC LIMIT 1')
    primero = c.fetchone()
    c.execute('SELECT * FROM snapshots ORDER BY id DESC LIMIT 1')
    ultimo = c.fetchone()
    c.execute('SELECT fecha, total_usd FROM snapshots WHERE fecha >= date("now", "-7 days") ORDER BY id ASC LIMIT 1')
    semana = c.fetchone()
    c.execute('SELECT fecha, total_usd FROM snapshots WHERE fecha >= date("now", "-30 days") ORDER BY id ASC LIMIT 1')
    mes = c.fetchone()
    c.execute('SELECT MAX(total_usd) FROM snapshots')
    maximo = c.fetchone()[0]
    c.execute('SELECT MIN(total_usd) FROM snapshots')
    minimo = c.fetchone()[0]
    conn.close()
    return {
        'primero': primero,
        'ultimo': ultimo,
        'semana': semana,
        'mes': mes,
        'maximo': maximo,
        'minimo': minimo
    }

def guardar_dividendo(ticker, monto, descripcion=""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO dividendos (fecha, ticker, monto, descripcion)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d"), ticker, monto, descripcion))
    conn.commit()
    conn.close()

def obtener_dividendos():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM dividendos ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def obtener_dividendos_total():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT SUM(monto) FROM dividendos')
    total = c.fetchone()[0] or 0
    conn.close()
    return total