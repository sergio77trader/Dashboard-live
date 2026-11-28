//@version=6
indicator("SLY | Smart Money (Barrida + CHoCH + OB/FVG)", overlay=true, max_boxes_count=300, max_lines_count=300, max_labels_count=300)

// ═══════════════════════════════════════════════════════════════════════════
// MODELO (reglas explícitas, sin mirar al futuro)
//  1) Swings: pivote de N velas a cada lado. Se CONFIRMA N velas después (el marcador se dibuja en su lugar real).
//  2) Estructura: cierre por encima del último swing high = ruptura alcista; por debajo del último swing low = bajista.
//     BOS = ruptura a favor de la tendencia previa. CHoCH = ruptura contra la tendencia previa.
//  3) Barrida de liquidez: la mecha supera el último swing y la vela CIERRA de vuelta dentro del rango.
//  4) Order Block (OB): vela contraria más cercana al punto de origen del movimiento que rompió la estructura.
//  5) FVG: hueco entre el máximo de la vela [2] y el mínimo de la vela actual (o al revés).
//  6) SETUP: barrida + ruptura de estructura dentro de X velas -> orden LÍMITE en el OB.
//     Stop: más allá de la mecha de la barrida (+ colchón ATR). Objetivo: R múltiplos.
//  La tabla cuenta resultados de los setups para tener una primera idea (NO es un backtest completo).
// ═══════════════════════════════════════════════════════════════════════════

// ---------- Inputs ----------
n          = input.int(5, "Largo del pivote (swing)", minval=2, group="Estructura")
showSwings = input.bool(true, "Mostrar swings", group="Estructura")
showStruct = input.bool(true, "Mostrar BOS / CHoCH", group="Estructura")
showSweep  = input.bool(false, "Mostrar barridas de liquidez", group="Estructura")
showOB     = input.bool(true, "Mostrar Order Blocks", group="Zonas")
showFVG    = input.bool(true, "Mostrar FVG", group="Zonas")
minFvgAtr  = input.float(0.3, "FVG mínimo (x ATR)", minval=0.0, step=0.1, group="Zonas")
maxZones   = input.int(6, "Máx. zonas activas por tipo", minval=1, group="Zonas")
showSetup  = input.bool(true, "Mostrar setups (entrada/stop/objetivo)", group="Setup")
sweepWin   = input.int(15, "Velas máx. entre barrida y ruptura", minval=1, group="Setup")
waitBars   = input.int(30, "Velas máx. esperando el retroceso", minval=1, group="Setup")
entryMode  = input.string("Borde OB", "Entrada en", options=["Borde OB", "50% OB"], group="Setup")
rr         = input.float(2.0, "Objetivo (múltiplo de R)", minval=0.5, step=0.5, group="Setup")
bufAtr     = input.float(0.1, "Colchón del stop (x ATR)", minval=0.0, step=0.05, group="Setup")
showTable  = input.bool(true, "Mostrar tabla de resultados", group="Setup")

// ---------- Sesgo de temporalidad mayor ----------
useHTF   = input.bool(true, "Filtrar por sesgo de temporalidad mayor", group="Sesgo (temporalidad mayor)")
htfAuto  = input.bool(true, "Elegir automática (4h/1h -> Diario, Diario -> Semanal)", group="Sesgo (temporalidad mayor)")
htfManual = input.timeframe("D", "Temporalidad mayor manual", group="Sesgo (temporalidad mayor)")
htfLen   = input.int(3, "Pivote en la temporalidad mayor", minval=2, group="Sesgo (temporalidad mayor)")
needPD   = input.bool(true, "Exigir descuento (largos) / premium (cortos)", group="Sesgo (temporalidad mayor)", tooltip="Largos solo por debajo del 50% del rango mayor; cortos solo por encima.")
showHtfLv = input.bool(true, "Mostrar rango y equilibrio de la temporalidad mayor", group="Sesgo (temporalidad mayor)")

cBull = color.new(#00c896, 0)
cBear = color.new(#ff4d6d, 0)
atr   = ta.atr(14)

// ---------- Swings ----------
ph = ta.pivothigh(high, n, n)
pl = ta.pivotlow(low, n, n)
plotshape(showSwings and not na(ph), "Swing High", shape.triangledown, location.abovebar, color.new(color.gray, 20), offset=-n, size=size.tiny)
plotshape(showSwings and not na(pl), "Swing Low", shape.triangleup, location.belowbar, color.new(color.gray, 20), offset=-n, size=size.tiny)

var float lastSH = na
var float lastSL = na
var int lastSHb = na
var int lastSLb = na
var bool shBroken = true
var bool slBroken = true
var int trend = 0

if not na(ph)
    lastSH := ph
    lastSHb := bar_index - n
    shBroken := false
if not na(pl)
    lastSL := pl
    lastSLb := bar_index - n
    slBroken := false

// ---------- Utilidad: Order Block ----------
// Busca el extremo (mínimo si es alcista, máximo si es bajista) desde originBar hasta hoy y toma
// la vela contraria más cercana a ese extremo (hasta 5 velas atrás).
f_ob(bool bull, int originBar) =>
    int span = math.min(bar_index - originBar, 100)
    float ext = bull ? 1e10 : -1e10
    int k = 0
    for i = 0 to span
        if bull ? low[i] < ext : high[i] > ext
            ext := bull ? low[i] : high[i]
            k := i
    int pick = k
    for j = k to k + 5
        if bull ? close[j] < open[j] : close[j] > open[j]
            pick := j
            break
    [high[pick], low[pick], bar_index - pick]

// ---------- Estructura en temporalidad mayor (sin mirar al futuro) ----------
f_trend(int len) =>
    float p_h = ta.pivothigh(high, len, len)
    float p_l = ta.pivotlow(low, len, len)
    var float sh = na
    var float sl = na
    var bool shb = true
    var bool slb = true
    var int tr = 0
    if not na(p_h)
        sh := p_h
        shb := false
    if not na(p_l)
        sl := p_l
        slb := false
    if not shb and close > sh
        shb := true
        tr := 1
    if not slb and close < sl
        slb := true
        tr := -1
    [tr, sh, sl]

f_htf(int len) =>
    [t, h, l] = f_trend(len)
    [t[1], h[1], l[1]]   // dato de la vela mayor ya CERRADA: no repinta

htfEff = htfAuto ? (timeframe.in_seconds() < 86400 ? "D" : "W") : htfManual
[dTrend, dHi, dLo] = request.security(syminfo.tickerid, htfEff, f_htf(htfLen), lookahead=barmerge.lookahead_on)
eqD = (dHi + dLo) / 2
plot(useHTF and showHtfLv ? dHi : na, "Máx. rango mayor", color.new(color.gray, 40), style=plot.style_stepline)
plot(useHTF and showHtfLv ? dLo : na, "Mín. rango mayor", color.new(color.gray, 40), style=plot.style_stepline)
plot(useHTF and showHtfLv ? eqD : na, "Equilibrio 50%", color.new(color.yellow, 50), style=plot.style_stepline, linewidth=1)

// ---------- Utilidad: mantener cajas (extender y retirar al mitigarse) ----------
f_update(array<box> boxes, array<float> lvls, bool bull, int maxN) =>
    int sz = array.size(boxes)
    if sz > 0
        for i = sz - 1 to 0
            box b = array.get(boxes, i)
            box.set_right(b, bar_index)
            float lv = array.get(lvls, i)
            if bull ? close < lv : close > lv
                array.remove(boxes, i)
                array.remove(lvls, i)
    while array.size(boxes) > maxN
        box.delete(array.shift(boxes))
        array.shift(lvls)

var array<box> obBullB = array.new<box>()
var array<float> obBullL = array.new<float>()
var array<box> obBearB = array.new<box>()
var array<float> obBearL = array.new<float>()
var array<box> fvgBullB = array.new<box>()
var array<float> fvgBullL = array.new<float>()
var array<box> fvgBearB = array.new<box>()
var array<float> fvgBearL = array.new<float>()

// ---------- Ruptura de estructura ----------
bullBreak = not na(lastSH) and not shBroken and close > lastSH
bearBreak = not na(lastSL) and not slBroken and close < lastSL
bullChoch = bullBreak and trend == -1
bearChoch = bearBreak and trend == 1

// ---------- Barridas ----------
sweepBull = not na(lastSL) and low < lastSL and close > lastSL and (bar_index - lastSLb) > n   // barre mínimos (liquidez vendedora)
sweepBear = not na(lastSH) and high > lastSH and close < lastSH and (bar_index - lastSHb) > n  // barre máximos (liquidez compradora)

var int sweepBullBar = na
var float sweepBullLow = na
var int sweepBearBar = na
var float sweepBearHigh = na

if sweepBull
    sweepBullLow := (na(sweepBullBar) or bar_index - sweepBullBar > sweepWin) ? low : math.min(sweepBullLow, low)
    sweepBullBar := bar_index
    if showSweep
        label.new(bar_index, low, "SSL", style=label.style_label_up, color=color.new(cBull, 60), textcolor=color.white, size=size.tiny)
if sweepBear
    sweepBearHigh := (na(sweepBearBar) or bar_index - sweepBearBar > sweepWin) ? high : math.max(sweepBearHigh, high)
    sweepBearBar := bar_index
    if showSweep
        label.new(bar_index, high, "BSL", style=label.style_label_down, color=color.new(cBear, 60), textcolor=color.white, size=size.tiny)

// ---------- Estado del setup ----------
var int setupDir = 0          // 1 largo, -1 corto, 0 ninguno
var float sEntry = na
var float sStop = na
var float sTp = na
var int sBar = na
var int fillBar = na
var bool sFilled = false
var line lnE = na
var line lnS = na
var line lnT = na
var int nSetups = 0
var int nFills = 0
var int nWins = 0
var int nLoss = 0
var int nCancel = 0
var float netR = 0.0

// Resolución de un setup abierto (usa solo información de velas posteriores a su creación)
int res = 0   // 1 TP, -1 SL, 2 cancelado
if setupDir != 0 and bar_index > sBar
    if not sFilled
        if bar_index - sBar > waitBars
            res := 2
        else if (setupDir == 1 ? low <= sEntry : high >= sEntry)
            sFilled := true
            fillBar := bar_index
            nFills += 1
            if setupDir == 1 ? low <= sStop : high >= sStop
                res := -1
    else if bar_index > fillBar
        if setupDir == 1 ? low <= sStop : high >= sStop
            res := -1           // si stop y objetivo caen en la misma vela, se asume el stop
        else if setupDir == 1 ? high >= sTp : low <= sTp
            res := 1

if res != 0
    if res == 1
        nWins += 1
        netR += rr
    else if res == -1
        nLoss += 1
        netR -= 1.0
    else
        nCancel += 1
    if showSetup
        line.set_x2(lnE, bar_index)
        line.set_x2(lnS, bar_index)
        line.set_x2(lnT, bar_index)
        label.new(bar_index, res == 1 ? sTp : (res == -1 ? sStop : sEntry), res == 1 ? "TP" : (res == -1 ? "SL" : "x"),
                  style=label.style_label_left, color=color.new(res == 1 ? cBull : (res == -1 ? cBear : color.gray), 40), textcolor=color.white, size=size.tiny)
    setupDir := 0
    sFilled := false

// ---------- Procesar rupturas (dibujo, OB y creación de setups) ----------
bool newLong = false
bool newShort = false

if bullBreak
    if showStruct
        line.new(lastSHb, lastSH, bar_index, lastSH, color=cBull, style=line.style_dashed)
        label.new(int(math.avg(lastSHb, bar_index)), lastSH, bullChoch ? "CHoCH" : "BOS", style=label.style_label_down, color=color.new(cBull, 70), textcolor=color.white, size=size.tiny)
    if showOB and not na(lastSLb)
        [t, b, bb] = f_ob(true, lastSLb)
        array.push(obBullB, box.new(bb, t, bar_index, b, bgcolor=color.new(cBull, 85), border_color=color.new(cBull, 40)))
        array.push(obBullL, b)
    if setupDir == 0 and not na(sweepBullBar) and bar_index - sweepBullBar <= sweepWin
        [t2, b2, bb2] = f_ob(true, sweepBullBar - 2)
        e = entryMode == "Borde OB" ? t2 : (t2 + b2) / 2
        s = math.min(b2, sweepBullLow) - bufAtr * atr
        okL = not useHTF or (dTrend == 1 and (not needPD or e < eqD))
        if e < close and e > s and okL
            setupDir := 1
            sEntry := e
            sStop := s
            sTp := e + rr * (e - s)
            sBar := bar_index
            sFilled := false
            nSetups += 1
            newLong := true
    shBroken := true
    trend := 1

if bearBreak
    if showStruct
        line.new(lastSLb, lastSL, bar_index, lastSL, color=cBear, style=line.style_dashed)
        label.new(int(math.avg(lastSLb, bar_index)), lastSL, bearChoch ? "CHoCH" : "BOS", style=label.style_label_up, color=color.new(cBear, 70), textcolor=color.white, size=size.tiny)
    if showOB and not na(lastSHb)
        [t3, b3, bb3] = f_ob(false, lastSHb)
        array.push(obBearB, box.new(bb3, t3, bar_index, b3, bgcolor=color.new(cBear, 85), border_color=color.new(cBear, 40)))
        array.push(obBearL, t3)
    if setupDir == 0 and not na(sweepBearBar) and bar_index - sweepBearBar <= sweepWin
        [t4, b4, bb4] = f_ob(false, sweepBearBar - 2)
        e2 = entryMode == "Borde OB" ? b4 : (t4 + b4) / 2
        s2 = math.max(t4, sweepBearHigh) + bufAtr * atr
        okS = not useHTF or (dTrend == -1 and (not needPD or e2 > eqD))
        if e2 > close and e2 < s2 and okS
            setupDir := -1
            sEntry := e2
            sStop := s2
            sTp := e2 - rr * (s2 - e2)
            sBar := bar_index
            sFilled := false
            nSetups += 1
            newShort := true
    slBroken := true
    trend := -1

if (newLong or newShort) and showSetup
    lnE := line.new(bar_index, sEntry, bar_index + waitBars, sEntry, color=color.new(color.white, 20), style=line.style_solid)
    lnS := line.new(bar_index, sStop, bar_index + waitBars, sStop, color=cBear, style=line.style_dotted)
    lnT := line.new(bar_index, sTp, bar_index + waitBars, sTp, color=cBull, style=line.style_dotted)
    label.new(bar_index, sEntry, (newLong ? "LONG límite " : "SHORT límite ") + str.tostring(sEntry, format.mintick),
              style=newLong ? label.style_label_up : label.style_label_down, color=newLong ? cBull : cBear, textcolor=color.white, size=size.small)

// ---------- FVG ----------
fvgBull = low > high[2] and (low - high[2]) > minFvgAtr * atr
fvgBear = high < low[2] and (low[2] - high) > minFvgAtr * atr
if showFVG and fvgBull
    array.push(fvgBullB, box.new(bar_index - 2, low, bar_index, high[2], bgcolor=color.new(color.teal, 85), border_color=color.new(color.teal, 60)))
    array.push(fvgBullL, high[2])
if showFVG and fvgBear
    array.push(fvgBearB, box.new(bar_index - 2, low[2], bar_index, high, bgcolor=color.new(color.orange, 85), border_color=color.new(color.orange, 60)))
    array.push(fvgBearL, low[2])

f_update(obBullB, obBullL, true, maxZones)
f_update(obBearB, obBearL, false, maxZones)
f_update(fvgBullB, fvgBullL, true, maxZones)
f_update(fvgBearB, fvgBearL, false, maxZones)

// ---------- Tabla ----------
var table tb = table.new(position.bottom_right, 2, 8, bgcolor=color.new(color.black, 20), border_width=1)
if showTable and barstate.islast
    int decided = nWins + nLoss
    table.cell(tb, 0, 0, "SLY Smart Money", text_color=color.white, text_size=size.small)
    table.cell(tb, 1, 0, "", text_color=color.white)
    table.cell(tb, 0, 1, "Setups", text_color=color.gray, text_size=size.small)
    table.cell(tb, 1, 1, str.tostring(nSetups), text_color=color.white, text_size=size.small)
    table.cell(tb, 0, 2, "Ejecutados", text_color=color.gray, text_size=size.small)
    table.cell(tb, 1, 2, str.tostring(nFills), text_color=color.white, text_size=size.small)
    table.cell(tb, 0, 3, "Ganados / Perdidos", text_color=color.gray, text_size=size.small)
    table.cell(tb, 1, 3, str.tostring(nWins) + " / " + str.tostring(nLoss), text_color=color.white, text_size=size.small)
    table.cell(tb, 0, 4, "Acierto", text_color=color.gray, text_size=size.small)
    table.cell(tb, 1, 4, decided > 0 ? str.tostring(nWins / decided * 100, "#.#") + "%" : "-", text_color=color.white, text_size=size.small)
    table.cell(tb, 0, 5, "Resultado (R)", text_color=color.gray, text_size=size.small)
    table.cell(tb, 1, 5, str.tostring(netR, "#.##"), text_color=netR >= 0 ? cBull : cBear, text_size=size.small)
    table.cell(tb, 0, 6, "Cancelados", text_color=color.gray, text_size=size.small)
    table.cell(tb, 1, 6, str.tostring(nCancel), text_color=color.white, text_size=size.small)

if showTable and barstate.islast
    table.cell(tb, 0, 7, "Sesgo " + htfEff, text_color=color.gray, text_size=size.small)
    table.cell(tb, 1, 7, dTrend == 1 ? "ALCISTA" : (dTrend == -1 ? "BAJISTA" : "-"), text_color=dTrend == 1 ? cBull : (dTrend == -1 ? cBear : color.gray), text_size=size.small)

alertcondition(newLong, "SLY SM LONG (orden límite)", "Setup LONG: barrida + ruptura. Orden límite en el OB.")
alertcondition(newShort, "SLY SM SHORT (orden límite)", "Setup SHORT: barrida + ruptura. Orden límite en el OB.")
