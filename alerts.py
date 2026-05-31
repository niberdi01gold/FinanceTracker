from binance_module import obtener_balance

ultimo_total = None
maximo_historico = None

def verificar_alertas():
    global ultimo_total, maximo_historico
    
    data = obtener_balance()
    
    if 'error' in data:
        return None
    
    total_actual = data['total']
    alertas = []

    # Alerta nuevo máximo histórico
    if maximo_historico is None or total_actual > maximo_historico:
        if maximo_historico is not None:
            alertas.append(
                f"🚀 *Nuevo máximo histórico*\n"
                f"Tu cartera alcanzó USD {total_actual:.2f}"
            )
        maximo_historico = total_actual

    # Alerta BTC sube o baja 5%
    if ultimo_total is not None:
        cambio_btc = ((data['btc_precio'] - ultimo_total) / ultimo_total) * 100
        if cambio_btc >= 5:
            alertas.append(
                f"📈 *BTC subió {cambio_btc:.1f}%*\n"
                f"Precio actual: USD {data['btc_precio']:,.2f}"
            )
        elif cambio_btc <= -5:
            alertas.append(
                f"📉 *BTC bajó {abs(cambio_btc):.1f}%*\n"
                f"Precio actual: USD {data['btc_precio']:,.2f}"
            )

    ultimo_total = data['btc_precio']