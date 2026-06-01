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
    data = obtener_balance()
    if 'error' not in data:
        alertas = verificar_alertas(data['total'])
    else:
        alertas = verificar_alertas()
    if alertas:
        for alerta in alertas:
            await enviar_mensaje(alerta)

# ── Comandos de Telegram ──

async def cmd_cartera(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    if 'error' in data:
        await update.message.reply_text(f"❌ Error: {data['error']}")
        return
    mensaje = (
        f"💼 *Tu Cartera Ahora*\n\n"
        f"₿ BTC: {data['btc_cantidad']:.6f} BTC\n"
        f"   Precio: USD {data['btc_precio']:,.2f}\n"
        f"   Valor: USD {data['btc_valor']:,.2f}\n\n"
        f"Ξ ETH: {data['eth_cantidad']:.6f} ETH\n"
        f"   Precio: USD {data['eth_precio']:,.2f}\n"
        f"   Valor: USD {data['eth_valor']:,.2f}\n\n"
        f"💰 Total: USD {data['total']:,.2f}"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    if 'error' in data:
        await update.message.reply_text(f"❌ Error: {data['error']}")
        return
    mensaje = (
        f"₿ *Bitcoin*\n\n"
        f"Precio: USD {data['btc_