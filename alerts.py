import pandas as pd
import ta
import requests
import yfinance as yf

maximo_historico = None
precios_anteriores = {}

TICKERS_IBKR = ['O', 'CEG', 'GEV', 'JNJ', 'ABBV', 'AVGO', 'AMD', 'MO', 'NVDA', 'RKLB']

def obtener_velas_coingecko(coin_id, dias=2):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {'vs_currency': 'usd', 'days': dias, 'interval': 'hourly'}
    r = requests.get(url, params=params)
    data = r.json()
    precios = [p[1] for p in data['prices']]
    df = pd.DataFrame({'close': precios})
    return df

def obtener_velas_accion(ticker):
    data = yf.download(ticker, period="3mo", interval="1d", progress=False)
    df = pd.DataFrame({'close': data['Close'].values.flatten()})
    return df

def calcular_indicadores(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['ema20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    return df

def analizar(nombre, df):
    alertas = []
    df = calcular_indicadores(df)
    precio = df['close'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    ema20 = df['ema20'].iloc[-1]
    ema50 = df['ema50'].iloc[-1]
    ema20_anterior = df['ema20'].iloc[-2]
    ema50_anterior = df['ema50'].iloc[-2]

    if rsi < 30:
        alertas.append(
            f"🟢 *{nombre} — Zona de compra*\n"
            f"RSI: {rsi:.1f} — Sobrevendido\n"
            f"Precio: USD {precio:,.2f}\n"
            f"📊 Posible oportunidad de compra"
        )
    elif rsi > 70:
        alertas.append(
            f"🔴 *{nombre} — Zona de venta*\n"
            f"RSI: {rsi:.1f} — Sobrecomprado\n"
            f"Precio: USD {precio:,.2f}\n"
            f"📊 Considera tomar ganancias"
        )

    if ema20_anterior < ema50_anterior and ema20 > ema50:
        alertas.append(
            f"📈 *{nombre} — Señal alcista*\n"
            f"EMA20 cruzó sobre EMA50\n"
            f"Precio: USD {precio:,.2f}\n"
            f"📊 Posible inicio de tendencia alcista"
        )
    elif ema20_anterior > ema50_anterior and ema20 < ema50:
        alertas.append(
            f"📉 *{nombre} — Señal bajista*\n"
            f"EMA20 cruzó bajo EMA50\n"
            f"Precio: USD {precio:,.2f}\n"
            f"📊 Posible inicio de tendencia bajista"
        )
    return alertas

def verificar_volatilidad_binance():
    global precios_anteriores
    alertas = []
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {'ids': 'bitcoin,ethereum', 'vs_currencies': 'usd', 'include_24hr_change': 'true'}
        r = requests.get(url, params=params)
        data = r.json()

        for coin_id, nombre in [('bitcoin', 'BTC'), ('ethereum', 'ETH')]:
            precio_actual = data[coin_id]['usd']
            cambio_24h = data[coin_id]['usd_24h_change']

            if coin_id in precios_anteriores:
                precio_anterior = precios_anteriores[coin_id]
                cambio = ((precio_actual - precio_anterior) / precio_anterior) * 100
                if abs(cambio) >= 3:
                    emoji = "🚀" if cambio > 0 else "💥"
                    alertas.append(
                        f"{emoji} *{nombre} — Movimiento brusco*\n"
                        f"Cambio: {'+' if cambio > 0 else ''}{cambio:.1f}% en la última hora\n"
                        f"Precio: USD {precio_actual:,.2f}\n"
                        f"Cambio 24h: {cambio_24h:+.1f}%"
                    )
            precios_anteriores[coin_id] = precio_actual
    except Exception as e:
        print(f"Error volatilidad Binance: {e}")
    return alertas

def verificar_alertas_binance(total_actual=None):
    global maximo_historico
    alertas = []

    for coin_id, nombre in [('bitcoin', 'BTC'), ('ethereum', 'ETH')]:
        try:
            df = obtener_velas_coingecko(coin_id)
            alertas += analizar(nombre, df)
        except Exception as e:
            alertas.append(f"⚠️ Error analizando {nombre}: {str(e)}")

    if total_actual:
        if maximo_historico is None or total_actual > maximo_historico:
            if maximo_historico is not None:
                alertas.append(
                    f"🚀 *Nuevo máximo histórico*\n"
                    f"Tu cartera alcanzó USD {total_actual:.2f}"
                )
            maximo_historico = total_actual

    return alertas

def verificar_alertas_ibkr():
    alertas = []
    for ticker in TICKERS_IBKR:
        try:
            df = obtener_velas_accion(ticker)
            alertas += analizar(ticker, df)
        except Exception as e:
            alertas.append(f"⚠️ Error analizando {ticker}: {str(e)}")
    return alertas

def verificar_alertas(total_actual=None):
    return verificar_alertas_binance(total_actual) + verificar_alertas_ibkr()