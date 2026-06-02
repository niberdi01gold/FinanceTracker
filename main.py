import asyncio
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from binance_module import obtener_balance
from ibkr_module import obtener_posiciones, obtener_valor_total
from database import init_db, guardar_snapshot, obtener_snapshot_ayer, obtener_snapshot_semana, obtener_rendimiento, obtener_dividendos, obtener_dividendos_total
from alerts import verificar_alertas_binance, verificar_alertas_ibkr, verificar_volatilidad_binance

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TICKERS_IBKR = ['O', 'CEG', 'GEV', 'JNJ', 'ABBV', 'AVGO', 'AMD', 'MO', 'NVDA', 'RKLB']

print(f"TOKEN cargado: {TELEGRAM_TOKEN[:10] if TELEGRAM_TOKEN else 'NONE'}...")
print(f"CHAT_ID cargado: {TELEGRAM_CHAT_ID}")

def mercado_abierto():
    ny = pytz.timezone('America/New_York')
    ahora = datetime.now(ny)
    if ahora.weekday() >= 5:
        return False
    hora = ahora.hour + ahora.minute / 60
    return 9.5 <= hora <= 16.0

async def enviar_mensaje(texto):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=texto, parse_mode='Markdown')

async def reporte_diario():
    data = obtener_balance()
    if 'error' in data:
        await enviar_mensaje(f"Error Binance: {data['error']}")
        return
    guardar_snapshot(data['btc_cantidad'], data['btc_valor'], data['eth_cantidad'], data['eth_valor'], data['total'])
    ayer = obtener_snapshot_ayer()
    ganancia_texto = ""
    if ayer:
        ganancia = data['total'] - ayer[6]
        porcentaje = (ganancia / ayer[6]) * 100
        emoji = "📈" if ganancia >= 0 else "📉"
        ganancia_texto = f"\n{emoji} Ganancia hoy: {'+' if ganancia >= 0 else ''}{ganancia:.2f} USD ({porcentaje:+.2f}%)"
    binance_msg = f"☀️ *Reporte Diario — Binance*\n\n₿ BTC: {data['btc_cantidad']:.6f}\nPrecio: USD {data['btc_precio']:,.2f}\nValor: USD {data['btc_valor']:,.2f}\n\nΞ ETH: {data['eth_cantidad']:.6f}\nPrecio: USD {data['eth_precio']:,.2f}\nValor: USD {data['eth_valor']:,.2f}\n\n💰 Total: USD {data['total']:,.2f}{ganancia_texto}"
    await enviar_mensaje(binance_msg)
    posiciones = obtener_posiciones()
    if isinstance(posiciones, list):
        total_valor = sum(p['valor_mercado'] for p in posiciones)
        total_ganancia = sum(p['ganancia_total'] for p in posiciones)
        ibkr_msg = "📊 *Reporte Diario — IBKR*\n\n"
        for i, pos in enumerate(posiciones):
            ticker = TICKERS_IBKR[i] if i < len(TICKERS_IBKR) else f"Pos{i+1}"
            ganancia = pos['ganancia_total']
            emoji = "📈" if ganancia >= 0 else "📉"
            ibkr_msg += f"{emoji} {ticker}: USD {pos['valor_mercado']:.2f} ({'+' if ganancia >= 0 else ''}{ganancia:.2f})\n"
        emoji_total = "📈" if total_ganancia >= 0 else "📉"
        ibkr_msg += f"\n💰 Total IBKR: USD {total_valor:.2f}"
        ibkr_msg += f"\n{emoji_total} P&G: {'+' if total_ganancia >= 0 else ''}{total_ganancia:.2f} USD"
        await enviar_mensaje(ibkr_msg)

async def reporte_semanal():
    data = obtener_balance()
    semana = obtener_snapshot_semana()
    rentabilidad_texto = ""
    if semana:
        capital_inicial = semana[6]
        ganancia = data['total'] - capital_inicial
        porcentaje = (ganancia / capital_inicial) * 100
        rentabilidad_texto = f"\n📊 Capital inicial: USD {capital_inicial:,.2f}\n📈 Rentabilidad: {porcentaje:+.2f}%\n💵 Ganancia: {'+' if ganancia >= 0 else ''}{ganancia:.2f} USD"
    mensaje = f"📊 *Reporte Semanal*\n\n₿ BTC: {data['btc_cantidad']:.6f}\nΞ ETH: {data['eth_cantidad']:.6f}\n\n💰 Total Binance: USD {data['total']:,.2f}{rentabilidad_texto}"
    await enviar_mensaje(mensaje)

async def alertas_binance():
    try:
        data = obtener_balance()
        total = data.get('total') if 'error' not in data else None
        alertas = verificar_alertas_binance(total)
        for alerta in alertas:
            await enviar_mensaje(alerta)
    except Exception as e:
        print(f"Error alertas Binance: {e}")

async def alertas_ibkr():
    if not mercado_abierto():
        return
    try:
        alertas = verificar_alertas_ibkr()
        for alerta in alertas:
            await enviar_mensaje(alerta)
    except Exception as e:
        print(f"Error alertas IBKR: {e}")

async def alerta_volatilidad():
    try:
        alertas = verificar_volatilidad_binance()
        for alerta in alertas:
            await enviar_mensaje(alerta)
    except Exception as e:
        print(f"Error volatilidad: {e}")

async def aviso_apertura_mercado():
    await enviar_mensaje("🔔 *Mercado abierto*\n\nActiva el Gateway de IBKR para ver tus acciones en tiempo real.")

async def aviso_cierre_mercado():
    await enviar_mensaje("🔔 *Mercado cerrado*\n\nPuedes apagar el Gateway de IBKR. Tus acciones están guardadas.")

async def cmd_mercado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ny = pytz.timezone('America/New_York')
    ahora = datetime.now(ny)
    hora_ny = ahora.strftime("%I:%M %p")
    dia = ahora.weekday()
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_nombre = dias_semana[dia]
    if mercado_abierto():
        minutos_cierre = int((16.0 - (ahora.hour + ahora.minute / 60)) * 60)
        hrs = minutos_cierre // 60
        mins = minutos_cierre % 60
        estado = f"🟢 *Mercado ABIERTO*\n\nHora NY: {hora_ny} ({dia_nombre})\nCierra en: {hrs}h {mins}m"
    elif dia >= 5:
        estado = f"🔴 *Mercado CERRADO*\n\nHora NY: {hora_ny} ({dia_nombre})\nAbre el lunes a las 9:30 AM"
    else:
        hora_actual = ahora.hour + ahora.minute / 60
        if hora_actual < 9.5:
            minutos_apertura = int((9.5 - hora_actual) * 60)
            hrs = minutos_apertura // 60
            mins = minutos_apertura % 60
            estado = f"🔴 *Mercado CERRADO*\n\nHora NY: {hora_ny} ({dia_nombre})\nAbre en: {hrs}h {mins}m"
        else:
            estado = f"🔴 *Mercado CERRADO*\n\nHora NY: {hora_ny} ({dia_nombre})\nAbre mañana a las 9:30 AM"
    await update.message.reply_text(estado, parse_mode='Markdown')

async def cmd_rendimiento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_rendimiento()
    if not data['primero'] or not data['ultimo']:
        await update.message.reply_text("⚠️ Aún no hay suficientes datos históricos.")
        return
    total_actual = data['ultimo'][6]
    total_inicial = data['primero'][6]
    rentabilidad_total = ((total_actual - total_inicial) / total_inicial) * 100
    ganancia_total = total_actual - total_inicial
    semana_texto = ""
    if data['semana']:
        total_semana = data['semana'][1]
        rent_semana = ((total_actual - total_semana) / total_semana) * 100
        semana_texto = f"\n📅 Esta semana: {rent_semana:+.2f}%"
    mes_texto = ""
    if data['mes']:
        total_mes = data['mes'][1]
        rent_mes = ((total_actual - total_mes) / total_mes) * 100
        mes_texto = f"\n📆 Este mes: {rent_mes:+.2f}%"
    mensaje = (
        f"📊 *Rendimiento Histórico*\n\n"
        f"💰 Capital inicial: USD {total_inicial:,.2f}\n"
        f"💰 Capital actual: USD {total_actual:,.2f}\n\n"
        f"📈 Rentabilidad total: {rentabilidad_total:+.2f}%\n"
        f"💵 Ganancia total: {'+' if ganancia_total >= 0 else ''}{ganancia_total:.2f} USD"
        f"{semana_texto}"
        f"{mes_texto}\n\n"
        f"🏆 Máximo histórico: USD {data['maximo']:,.2f}\n"
        f"📉 Mínimo histórico: USD {data['minimo']:,.2f}"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_dividendos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dividendos = obtener_dividendos()
    total = obtener_dividendos_total()
    if not dividendos:
        await update.message.reply_text(
            "💰 *Dividendos*\n\nAún no hay dividendos registrados.\n\nCuando recibas un dividendo escribe:\n`/agregar_dividendo TICKER MONTO`\n\nEjemplo:\n`/agregar_dividendo ABBV 2.50`",
            parse_mode='Markdown'
        )
        return
    mensaje = f"💰 *Dividendos Recibidos*\n\n"
    for div in dividendos[-10:]:
        mensaje += f"📅 {div[1]} — {div[2]}: USD {div[3]:.2f}\n"
    mensaje += f"\n💵 Total acumulado: USD {total:.2f}"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_agregar_dividendo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import guardar_dividendo
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Uso: /agregar_dividendo TICKER MONTO\nEjemplo: /agregar_dividendo ABBV 2.50")
            return
        ticker = args[0].upper()
        monto = float(args[1])
        guardar_dividendo(ticker, monto)
        await update.message.reply_text(f"✅ Dividendo registrado\n{ticker}: USD {monto:.2f}", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    posiciones = obtener_posiciones()
    binance_total = data.get('total', 0) if 'error' not in data else 0
    ibkr_total = 0
    ibkr_ganancia = 0
    if isinstance(posiciones, list):
        ibkr_total = sum(p['valor_mercado'] for p in posiciones)
        ibkr_ganancia = sum(p['ganancia_total'] for p in posiciones)
    patrimonio = binance_total + ibkr_total
    emoji_ibkr = "📈" if ibkr_ganancia >= 0 else "📉"
    ibkr_status = f"USD {ibkr_total:,.2f} ({'+' if ibkr_ganancia >= 0 else ''}{ibkr_ganancia:.2f})" if isinstance(posiciones, list) else "⚠️ Offline"
    mensaje = (
        f"📋 *Resumen Completo*\n\n"
        f"₿ Binance: USD {binance_total:,.2f}\n"
        f"{emoji_ibkr} IBKR: {ibkr_status}\n\n"
        f"🏦 *Patrimonio Total: USD {patrimonio:,.2f}*\n\n"
        f"Mercado: {'🟢 Abierto' if mercado_abierto() else '🔴 Cerrado'}"
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_cartera(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    if 'error' in data:
        await update.message.reply_text(f"Error: {data['error']}")
        return
    mensaje = f"💼 *Cartera Binance*\n\n₿ BTC: {data['btc_cantidad']:.6f}\nPrecio: USD {data['btc_precio']:,.2f}\nValor: USD {data['btc_valor']:,.2f}\n\nΞ ETH: {data['eth_cantidad']:.6f}\nPrecio: USD {data['eth_precio']:,.2f}\nValor: USD {data['eth_valor']:,.2f}\n\n💰 Total: USD {data['total']:,.2f}"
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

async def cmd_ibkr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posiciones = obtener_posiciones()
    if isinstance(posiciones, dict) and 'error' in posiciones:
        await update.message.reply_text(
            "⚠️ *IBKR Offline*\n\nEl Gateway de IBKR no está activo.\n\nPara activarlo en tu PC:\n1. Ejecuta el Gateway\n2. Inicia sesión en localhost:5000\n3. Ejecuta ngrok",
            parse_mode='Markdown'
        )
        return
    total_valor = 0
    total_ganancia = 0
    mensaje = "📊 *Cartera IBKR*\n\n"
    for i, pos in enumerate(posiciones):
        ticker = TICKERS_IBKR[i] if i < len(TICKERS_IBKR) else f"Pos{i+1}"
        ganancia = pos['ganancia_total']
        emoji = "📈" if ganancia >= 0 else "📉"
        total_valor += pos['valor_mercado']
        total_ganancia += ganancia
        mensaje += f"{emoji} {ticker}: USD {pos['valor_mercado']:.2f} ({'+' if ganancia >= 0 else ''}{ganancia:.2f})\n"
    emoji_total = "📈" if total_ganancia >= 0 else "📉"
    mensaje += f"\n💰 Total: USD {total_valor:.2f}"
    mensaje += f"\n{emoji_total} P&G: {'+' if total_ganancia >= 0 else ''}{total_ganancia:.2f} USD"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = obtener_balance()
    posiciones = obtener_posiciones()
    binance_total = data.get('total', 0) if 'error' not in data else 0
    ibkr_total = sum(p['valor_mercado'] for p in posiciones) if isinstance(posiciones, list) else 0
    patrimonio = binance_total + ibkr_total
    mensaje = f"💰 *Patrimonio Total*\n\n📈 Binance: USD {binance_total:,.2f}\n📊 IBKR: USD {ibkr_total:,.2f}\n\n🏦 Total: USD {patrimonio:,.2f}"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = "🤖 *FinanceTracker — Comandos*\n\n/resumen — Todo en uno\n/cartera — Cartera Binance\n/ibkr — Cartera IBKR\n/total — Patrimonio total\n/mercado — Estado del mercado\n/rendimiento — Historial de rentabilidad\n/dividendos — Ver dividendos\n/agregar_dividendo — Registrar dividendo\n/btc — Precio BTC\n/eth — Precio ETH\n/ayuda — Ver esta lista"
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def main():
    print("Iniciando sistema...")
    init_db()
    print("Base de datos iniciada")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("resumen", cmd_resumen))
    app.add_handler(CommandHandler("cartera", cmd_cartera))
    app.add_handler(CommandHandler("btc", cmd_btc))
    app.add_handler(CommandHandler("eth", cmd_eth))
    app.add_handler(CommandHandler("ibkr", cmd_ibkr))
    app.add_handler(CommandHandler("total", cmd_total))
    app.add_handler(CommandHandler("mercado", cmd_mercado))
    app.add_handler(CommandHandler("rendimiento", cmd_rendimiento))
    app.add_handler(CommandHandler("dividendos", cmd_dividendos))
    app.add_handler(CommandHandler("agregar_dividendo", cmd_agregar_dividendo))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    scheduler = AsyncIOScheduler(timezone="America/Santiago")
    scheduler.add_job(reporte_diario, 'cron', hour=8, minute=0)
    scheduler.add_job(reporte_semanal, 'cron', day_of_week='mon', hour=8, minute=0)
    scheduler.add_job(alertas_binance, 'interval', hours=4)
    scheduler.add_job(alertas_ibkr, 'interval', minutes=30)
    scheduler.add_job(alerta_volatilidad, 'interval', minutes=60)
    scheduler.add_job(aviso_apertura_mercado, 'cron', day_of_week='mon-fri', hour=9, minute=30, timezone="America/New_York")
    scheduler.add_job(aviso_cierre_mercado, 'cron', day_of_week='mon-fri', hour=16, minute=0, timezone="America/New_York")
    scheduler.start()
    await enviar_mensaje("✅ *FinanceTracker iniciado*\n\nComandos:\n/resumen /cartera /ibkr /total\n/mercado /rendimiento /dividendos\n/btc /eth /ayuda")
    print("Bot iniciado con comandos")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())