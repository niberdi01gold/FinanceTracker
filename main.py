import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from binance_module import obtener_balance
from database import init_db, guardar_snapshot, obtener_snapshot_ayer, obtener_snapshot_semana
from alerts import verificar_alertas

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

async def enviar_mensaje(texto):
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=texto,
        parse_mode='Markdown'
    )

async def reporte_diario():
    data = obtener_balance()
    if 'error' in data:
        await enviar_mensaje(f"❌ Error al obtener balance: {data['error']}")
        return

    guardar_snapshot(
        data['btc_cantidad'], data['btc_valor'],
        data['eth_cantidad'], data['eth_valor'],
        data['total']
    )

    ayer = obtener_snapshot_ayer()
    ganancia_texto = ""
    if ayer:
        ganancia = data['total'] - ayer[6]
        porcentaje = (ganancia / ayer[6]) * 100
        emoji = "📈" if ganancia >= 0 else "📉"
        ganancia_texto = f"\n{emoji} Ganancia hoy: {'+' if ganancia >= 0 else ''}{ganancia:.2f} USD ({porcentaje:+.2f}%)"

    mensaje = (
        f"☀️ *Reporte Diario — Binance*\n\n"
        f"₿ BTC: {data['btc_cantidad']:.6f} BTC\n"
        f"   Precio: USD {data['btc_precio']:,.2f}\n"
        f"   Valor: USD {data['btc_valor']:,.2f}\n\n"
        f"Ξ ETH: {data['eth_cantidad']:.6f} ETH\n"
        f"   Precio: USD {data['eth_precio']:,.2f}\n"
        f"   Valor: USD {data['eth_valor']:,.2f}\n\n"
        f"💰 Total: USD {data['total']:,.2f}"
        f"{ganancia_texto}"
    )
    await enviar_mensaje(mensaje)

async def reporte_semanal():
    data = obtener_balance()
    semana = obtener_snapshot_semana()

    rentabilidad_texto = ""
    if semana:
        capital_inicial = semana[6]
        ganancia = data['total'] - capital_inicial
        porcentaje = (ganancia / capital_inicial) * 100
        rentabilidad_texto = (
            f"\n📊 Capital inicial: USD {capital_inicial:,.2f}\n"
            f"📈 Rentabilidad: {porcentaje:+.2f}%\n"
            f"💵 Ganancia: {'+' if ganancia >= 0 else ''}{ganancia:.2f} USD"
        )

    mensaje = (
        f"📊 *Reporte Semanal — Binance*\n\n"
        f"₿ BTC: {data['btc_cantidad']:.6f} BTC\n"
        f"Ξ ETH: {data['eth_cantidad']:.6f} ETH\n\n"
        f"💰 Total actual: USD {data['total']:,.2f}"
        f"{rentabilidad_texto}"
    )
    await enviar_mensaje(mensaje)

async def verificar_y_alertar():
    alertas = verificar_alertas()
    if alertas:
        for alerta in alertas:
            await enviar_mensaje(alerta)

async def main():
    init_db()
    await enviar_mensaje("✅ *FinanceTracker iniciado correctamente*\nReportes diarios a las 8:00 AM")

    scheduler = AsyncIOScheduler(timezone="America/Santiago")
    scheduler.add_job(reporte_diario, 'cron', hour=8, minute=0)
    scheduler.add_job(reporte_semanal, 'cron', day_of_week='mon', hour=8, minute=0)
    scheduler.add_job(verificar_y_alertar, 'interval', minutes=5)
    scheduler.start()

    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())