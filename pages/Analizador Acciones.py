//@version=5
strategy("SystemaTrader: HA Matrix + ADX [Con Fechas]", overlay=true, initial_capital=1000, default_qty_type=strategy.percent_of_equity, default_qty_value=100)

// --- 1. CONFIGURACIÓN ---
group_adx = "Configuración ADX"
adx_len = input.int(14, title="Longitud ADX", group=group_adx)
adx_th_micro = input.int(25, title="Umbral ADX (Gatillo)", group=group_adx)
adx_th_macro = input.int(20, title="Umbral ADX Diario (Filtro)", group=group_adx)

group_tf = "Temporalidades (Deben ser mayores a la del gráfico)"
tf_4h = input.timeframe("240", title="TF Intermedio (4H)", group=group_tf)
tf_1d = input.timeframe("D", title="TF Macro 1 (Diario)", group=group_tf)
tf_1w = input.timeframe("W", title="TF Macro 2 (Semanal)", group=group_tf)

// --- 2. CÁLCULO HEIKIN ASHI ---
is_ha_green() =>
    haClose = (open + high + low + close) / 4
    haOpen = float(na)
    haOpen := na(haOpen[1]) ? (open + close) / 2 : (haOpen[1] + haClose[1]) / 2
    haClose > haOpen

// --- 3. DATOS DE OTRAS TEMPORALIDADES ---
ha_4h_green = request.security(syminfo.tickerid, tf_4h, is_ha_green())
ha_1d_green = request.security(syminfo.tickerid, tf_1d, is_ha_green())
ha_1w_green = request.security(syminfo.tickerid, tf_1w, is_ha_green())

// --- 4. ADX ---
calc_adx(len) =>
    up = ta.change(high)
    down = -ta.change(low)
    plusDM = na(up) ? na : (up > down and up > 0 ? up : 0)
    minusDM = na(down) ? na : (down > up and down > 0 ? down : 0)
    tr = ta.rma(ta.tr, len)
    plus = fixnan(100 * ta.rma(plusDM, len) / tr)
    minus = fixnan(100 * ta.rma(minusDM, len) / tr)
    sum = plus + minus
    adx_val = 100 * ta.rma(math.abs(plus - minus) / (sum == 0 ? 1 : sum), len)
    adx_val

adx_micro = calc_adx(adx_len)
adx_macro = request.security(syminfo.tickerid, tf_1d, calc_adx(adx_len))

// --- 5. LÓGICA ---
ha_current_green = is_ha_green()

// LONG
trend_aligned_bull = ha_current_green and ha_4h_green and ha_1d_green and ha_1w_green
momentum_bull = (adx_macro > adx_th_macro) and (adx_micro > adx_th_micro)
enter_long = trend_aligned_bull and momentum_bull

// SHORT
trend_aligned_bear = not ha_current_green and not ha_4h_green and not ha_1d_green and not ha_1w_green
momentum_bear = (adx_macro > adx_th_macro) and (adx_micro > adx_th_micro)
enter_short = trend_aligned_bear and momentum_bear

// SALIDAS
exit_long = not ha_current_green
exit_short = ha_current_green

// --- 6. EJECUCIÓN ---
if (enter_long)
    strategy.entry("Long", strategy.long)
if (exit_long)
    strategy.close("Long")
if (enter_short)
    strategy.entry("Short", strategy.short)
if (exit_short)
    strategy.close("Short")

// --- 7. VISUALIZACIÓN ---
bgcolor(trend_aligned_bull ? color.new(color.green, 90) : na, title="Fondo Alcista")
bgcolor(trend_aligned_bear ? color.new(color.red, 90) : na, title="Fondo Bajista")

// --- 8. DASHBOARD DE INFORMACIÓN (NUEVO) ---

// Variables persistentes para guardar la fecha
var int last_entry_time = 0
var float last_entry_price = 0.0
var string last_signal_type = "Esperando..."

if (enter_long)
    last_entry_time := time
    last_entry_price := close
    last_signal_type := "LONG 🟢"

if (enter_short)
    last_entry_time := time
    last_entry_price := close
    last_signal_type := "SHORT 🔴"

// Función para formatear fecha (DD/MM/AAAA)
format_date(t) =>
    str.tostring(dayofmonth(t), "00") + "/" + str.tostring(month(t), "00") + "/" + str.tostring(year(t), "")

// Calcular rendimiento actual si hay posición
float pnl_pct = 0.0
if strategy.position_size > 0
    pnl_pct := ((close - strategy.position_avg_price) / strategy.position_avg_price) * 100
else if strategy.position_size < 0
    pnl_pct := ((strategy.position_avg_price - close) / strategy.position_avg_price) * 100

// Dibujar Tabla
var tbl = table.new(position.top_right, 2, 5, bgcolor = color.new(color.black, 50), border_width = 1)

if barstate.islast
    // Encabezado
    table.cell(tbl, 0, 0, "SystemaTrader Matrix", text_color = color.white, bgcolor=color.new(color.blue, 60), text_size=size.small, merge_cells=true)
    
    // Última Señal Detectada
    table.cell(tbl, 0, 1, "Última Señal:", text_color = color.white, text_halign=text.align_left)
    table.cell(tbl, 1, 1, last_signal_type, text_color = color.white, text_halign=text.align_right)
    
    // Fecha
    table.cell(tbl, 0, 2, "Fecha Entrada:", text_color = color.white, text_halign=text.align_left)
    table.cell(tbl, 1, 2, last_entry_time > 0 ? format_date(last_entry_time) : "-", text_color = color.yellow, text_halign=text.align_right)
    
    // Precio
    table.cell(tbl, 0, 3, "Precio Entrada:", text_color = color.white, text_halign=text.align_left)
    table.cell(tbl, 1, 3, last_entry_price > 0 ? str.tostring(last_entry_price, "#.##") : "-", text_color = color.white, text_halign=text.align_right)

    // Estado Actual
    status_txt = strategy.position_size != 0 ? "ABIERTA (" + str.tostring(pnl_pct, "#.##") + "%)" : "CERRADA"
    status_col = strategy.position_size != 0 ? (pnl_pct >= 0 ? color.green : color.red) : color.gray
    
    table.cell(tbl, 0, 4, "Estado Trade:", text_color = color.white, text_halign=text.align_left)
    table.cell(tbl, 1, 4, status_txt, text_color = status_col, text_halign=text.align_right, text_style=shape.label_down)
