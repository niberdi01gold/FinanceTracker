import pandas as pd
import ta
from binance.client import Client
from dotenv import load_dotenv
import os

load_dotenv()

client = Client(os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_SECRET_KEY"))

maximo_historico = None

def obtener_velas(symbol, intervalo="1h", limite=100):
    velas = client.get_klines(symbol=symbol, interval=intervalo, limit=limite)
    df = pd.DataFrame(velas, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    return df

def calcular_indicadores(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['ema20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    return df

def verificar_alertas(total_actual=None):
    global maximo_historico
    alertas = []

    for symbol, nombre in [('BTCUSDT', 'BTC'), ('ETHUSDT', 'ETH')]:
        try:
            df = obtener_velas(symbol)
            df = calcular_indicadores(df)

            precio = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            ema20 = df['ema20'].iloc[-1]
            ema50 = df['ema50'].iloc[-1]
            ema20_anterior = df['ema20'].iloc[-2]
            ema50_anterior = df['ema50'].iloc[-2]

            # Alerta RSI sobrevendido
            if rsi < 30:
                alertas.append(
                    f"🟢 *{nombre} — Zona de compra*\n"
                    f"RSI: {rsi:.1f} — Sobrevendido\n"
                    f"Precio: USD {precio:,.2f}\n"
                    f"📊 Posible oportunidad de compra"
                )

            # Alerta RSI sobrecomprado
            elif rsi > 70:
                alertas.append(
                    f"🔴 *{nombre} — Zona de venta*\n"
                    f"RSI: {rsi:.1f} — Sobrecomprado\n"
                    f"Precio: USD {precio:,.2f}\n"
                    f"📊 Considera tomar ganancias"
                )

            # Cruce alcista EMA20 sobre EMA50
            if ema20_anterior < ema50_anterior and ema20 > ema50:
                alertas.append(
                    f"📈 *{nombre} — Señal alcista*\n"
                    f"EMA20 cruzó sobre EMA50\n"
                    f"Precio: USD {precio:,.2f}\n"
                    f"📊 Posible inicio de tendencia alcista"
                )

            # Cruce bajista EMA20 bajo EMA50
            elif ema20_anterior > ema50_anterior and ema20 < ema50:
                alertas.append(
                    f"📉 *{nombre} — Señal bajista*\n"
                    f"EMA20 cruzó bajo EMA50\n"
                    f"Precio: USD {precio:,.2f}\n"
                    f"📊 Posible inicio de tendencia bajista"
                )

        except Exception as e:
            alertas.append(f"⚠️ Error analizando {nombre}: {str(e)}")

    # Alerta nuevo máximo histórico
    if total_actual:
        if maximo_historico is None or total_actual > maximo_historico:
            if maximo_historico is not None:
                alertas.append(
                    f"🚀 *Nuevo máximo histórico*\n"
                    f"Tu cartera alcanzó USD {total_actual:.2f}"
                )
            maximo_historico = total_actual

    return alertas