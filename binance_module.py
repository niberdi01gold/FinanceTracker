from binance.client import Client
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_SECRET_KEY")

def obtener_cliente():
    return Client(api_key, api_secret)

def obtener_balance():
    try:
        client = obtener_cliente()
        btc_balance = float(client.get_asset_balance(asset='BTC')['free'])
        eth_balance = float(client.get_asset_balance(asset='ETH')['free'])

        btc_precio = float(client.get_symbol_ticker(symbol='BTCUSDT')['price'])
        eth_precio = float(client.get_symbol_ticker(symbol='ETHUSDT')['price'])

        btc_valor = btc_balance * btc_precio
        eth_valor = eth_balance * eth_precio
        total = btc_valor + eth_valor

        return {
            'btc_cantidad': btc_balance,
            'btc_precio': btc_precio,
            'btc_valor': btc_valor,
            'eth_cantidad': eth_balance,
            'eth_precio': eth_precio,
            'eth_valor': eth_valor,
            'total': total
        }
    except Exception as e:
        return {'error': str(e)}