import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from binance_module import obtener_balance
from database import init_db, guardar_snapshot, obtener_snapshot_ayer, obtener_snapshot_semana
from alerts import verificar_alertas

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print(f"TOKEN cargado: {TELEGRAM_TOKEN[:10] if TELEGRAM_TOKEN else 'NONE'}...")
print(f"CHAT_ID cargado: {TELEGRAM_CHAT_ID}")

async def enviar_mensaje(texto):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=texto, parse_mode='Markdown')

async def reporte_diario():
    data = obtener_balance()
    if 'error' in data:
        await enviar_mensaje(f"Error al obtener balance: {data['error']}")
        return
    guardar_snapshot(data['btc_cantidad'], data['btc_valor'], data['eth_cantidad'], data['eth_valor'], data['total'])
    ayer = obtener_snapshot_ayer()
    ganancia_texto = ""
    if ayer:
        ganancia = data['total'] - ayer[6]
        porcentaje = (ganancia / ayer[6]) * 100
        emoji = "📈" if ganancia >= 0 else "📉"
        ganancia_texto = f"\n{emoji} Ganancia hoy: {'+' if ganancia >= 0 else ''}{ganancia:.2f} USD ({porcentaje:+.2f}%)"
    mensaje = f"☀️ *Reporte Diario*\n\n₿ BTC: {data['btc_cantidad']:.6f}\nPrecio: USD {data['btc_precio']:,.2f}\nValor: USD {data['btc_valor']:,.2f}\n\nΞ ETH: {data['eth_cantidad']:.6f}\nPrecio: USD {data['eth_precio']:,.2f}\nValor: USD {data['eth_valor']:,.2f}\n\n💰 Total: USD {data['total']:,.2f}{ganancia_texto}"
    await enviar_mensaje(mensaje)

async def reporte_semanal():
    data = obtener_balance()
    semana = obtener_snapshot_semana()
    rentabilidad_texto = ""
    if semana:
        capital_inicial = semana[6]
        ganancia = data['total'] - capital_inicial
        porcentaje = (ganancia / capital_inicial) * 100
        rentabilidad_texto = f"\n📊 Capital inicial: USD {capital_inicial:,.2f}\n📈 Rentabilidad: {porcentaje:+.2f}%\n💵 Ganancia: {'+' if ganancia >= 0 else ''}{ganancia:.2f} USD"
    mensaje = f"📊 *Reporte Semanal*\n\n₿ BTC: {data['btc_cantidad']:.6f}\nΞ ETH: {data['eth_cantidad']:.6f}\n\n💰 Total: USD {data['total']:,.2f}{rentabilidad_texto}"
    await enviar_mensaje(mensaje)

async def verificar_y_alertar():
    data = obtener_balance()
    if 'error' not in data:
        alertas = verificar_alertas(data['total'])
    else:
        alertas = verificar_alertas()
    if alertas:
        for alerta in alertas:
            await enviar_mensaje(alerta)

async def cmd_cartera(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    if 'error' in data:
        await update.message.reply_text(f"Error: {data['error']}")
        return
    mensaje = f"💼 *Tu Cartera Ahora*\n\n₿ BTC: {data['btc_cantidad']:.6f}\nPrecio: USD {data['btc_precio']:,.2f}\nValor: USD {data['btc_valor']:,.2f}\n\nΞ ETH: {data['eth_cantidad']:.6f}\nPrecio: USD {data['eth_precio']:,.2f}\nValor: USD {data['eth_valor']:,.2f}\n\n💰 Total: USD {data['total']:,.2f}"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    if 'error' in data:
        await update.message.reply_text(f"Error: {data['error']}")
        return
    mensaje = f"₿ *Bitcoin*\n\nPrecio: USD {data['btc_precio']:,.2f}\nBalance: {data['btc_cantidad']:.6f} BTC\nValor: USD {data['btc_valor']:,.2f}"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_eth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    if 'error' in data:
        await update.message.reply_text(f"Error: {data['error']}")
        return
    mensaje = f"Ξ *Ethereum*\n\nPrecio: USD {data['eth_precio']:,.2f}\nBalance: {data['eth_cantidad']:.6f} ETH\nValor: USD {data['eth_valor']:,.2f}"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = "🤖 *FinanceTracker — Comandos*\n\n/cartera — Ver tu cartera completa\n/btc — Ver precio y balance de BTC\n/eth — Ver precio y balance de ETH\n/ayuda — Ver esta lista"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def main():
    print("Iniciando sistema...")
    init_db()
    print("Base de datos iniciada")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("cartera", cmd_cartera))
    app.add_handler(CommandHandler("btc", cmd_btc))
    app.add_handler(CommandHandler("eth", cmd_eth))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    scheduler = AsyncIOScheduler(timezone="America/Santiago")
    scheduler.add_job(reporte_diario, 'cron', hour=8, minute=0)
    scheduler.add_job(reporte_semanal, 'cron', day_of_week='mon', hour=8, minute=0)
    scheduler.add_job(verificar_y_alertar, 'interval', minutes=5)
    scheduler.start()
    await enviar_mensaje("✅ *FinanceTracker iniciado*\n\nComandos:\n/cartera\n/btc\n/eth\n/ayuda")
    print("Bot iniciado con comandos")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())