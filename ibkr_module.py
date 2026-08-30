import requests
import urllib3
import os
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

BASE_URL = f"{os.getenv('IBKR_URL', 'https://localhost:5000')}/v1/api"
ACCOUNT_ID = os.getenv("IBKR_ACCOUNT_ID")

def obtener_posiciones():
    try:
        url = f"{BASE_URL}/portfolio/{ACCOUNT_ID}/positions/0"
        response = requests.get(url, verify=False)
        if response.status_code != 200:
            return {'error': f"Error {response.status_code}"}
        
        posiciones = response.json()
        resultado = []
        
        for pos in posiciones:
            resultado.append({
                'ticker': pos.get('ticker', ''),
                'nombre': pos.get('name', ''),
                'cantidad': pos.get('position', 0),
                'precio_actual': pos.get('mktPrice', 0),
                'valor_mercado': pos.get('mktValue', 0),
                'costo_base': pos.get('avgCost', 0),
                'ganancia_dia': pos.get('dailyPnL', 0),
                'ganancia_total': pos.get('unrealizedPnl', 0),
            })
        
        return resultado
    except Exception as e:
        return {'error': str(e)}

def obtener_valor_total():
    try:
        url = f"{BASE_URL}/portfolio/{ACCOUNT_ID}/summary"
        response = requests.get(url, verify=False)
        if response.status_code != 200:
            return {'error': f"Error {response.status_code}"}
        
        data = response.json()
        valor_neto = data.get('netliquidation', {}).get('amount', 0)
        ganancia_dia = data.get('dailypnl', {}).get('amount', 0)
        
        return {
            'valor_total': valor_neto,
            'ganancia_dia': ganancia_dia
        }
    except Exception as e:
        return {'error': str(e)}
