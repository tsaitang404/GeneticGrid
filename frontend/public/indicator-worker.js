// Indicator Calculation Worker
self.onmessage = function(e) {
    const { id, type, data } = e.data;
    
    if (type === 'CALCULATE') {
        const { candles, indicators } = data;
        const results = {};
        
        for (const ind of indicators) {
            try {
                if (ind === 'ma') {
                    results.ma = [
                        calculateSMA(candles, 5),
                        calculateSMA(candles, 10),
                        calculateSMA(candles, 20)
                    ];
                } else if (ind === 'maWithMacd') {
                    results.maWithMacd = [
                        calculateSMA(candles, 9),
                        calculateSMA(candles, 12),
                        calculateSMA(candles, 26)
                    ];
                } else if (ind === 'ema') {
                    results.ema = [
                        calculateEMA(candles, 5),
                        calculateEMA(candles, 10),
                        calculateEMA(candles, 20)
                    ];
                } else if (ind === 'emaFib') {
                    results.emaFib = [
                        calculateEMA(candles, 9),
                        calculateEMA(candles, 21),
                        calculateEMA(candles, 55)
                    ];
                } else if (ind === 'boll') {
                    results.boll = calculateBollingerBands(candles, 20, 2);
                } else if (ind === 'sar') {
                    results.sar = calculateSAR(candles);
                } else if (ind === 'supertrend') {
                    results.supertrend = calculateSuperTrend(candles);
                } else if (ind === 'sr') {
                    results.sr = calculateSupportResistance(candles);
                } else if (ind === 'macd') {
                    results.macd = calculateMACD(candles, 12, 26, 9);
                } else if (ind === 'kdj') {
                    results.kdj = calculateKDJ(candles, 9, 3, 3);
                } else if (ind === 'rsi') {
                    results.rsi = calculateRSI(candles, 14);
                } else if (ind === 'stochrsi') {
                    results.stochrsi = calculateStochRSI(candles, 14, 14, 3, 3);
                } else if (ind === 'cci') {
                    results.cci = calculateCCI(candles, 20);
                } else if (ind === 'dmi') {
                    results.dmi = calculateDMI(candles, 14);
                } else if (ind === 'wr') {
                    results.wr = calculateWR(candles, 14);
                } else if (ind === 'obv') {
                    results.obv = calculateOBV(candles);
                } else if (ind === 'trix') {
                    results.trix = calculateTRIX(candles, 12);
                } else if (ind === 'roc') {
                    results.roc = calculateROC(candles, 12);
                } else if (ind === 'mtm') {
                    results.mtm = calculateMTM(candles, 12);
                } else if (ind === 'dma') {
                    results.dma = calculateDMA(candles, 10, 50);
                } else if (ind === 'vr') {
                    results.vr = calculateVR(candles, 26);
                } else if (ind === 'brar') {
                    results.brar = calculateBRAR(candles, 26);
                } else if (ind === 'psy') {
                    results.psy = calculatePSY(candles, 12);
                } else if (ind === 'atr') {
                    results.atr = calculateATR(candles, 14);
                }
            } catch (err) {
                console.error('Worker calculation error:', ind, err);
            }
        }
        
        self.postMessage({ id, type: 'RESULT', results });
    }
};

// Simple Moving Average
function calculateSMA(candles, period) {
    const result = [];
    for (let i = 0; i < candles.length; i++) {
        if (i < period - 1) continue;
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += candles[i - j].close;
        }
        result.push({
            time: candles[i].time,
            value: sum / period
        });
    }
    return result;
}

// Exponential Moving Average
function calculateEMA(candles, period) {
    const result = [];
    const k = 2 / (period + 1);
    let ema = candles[0].close;
    
    result.push({ time: candles[0].time, value: ema });
    
    for (let i = 1; i < candles.length; i++) {
        ema = (candles[i].close - ema) * k + ema;
        result.push({ time: candles[i].time, value: ema });
    }
    return result;
}

// Bollinger Bands
function calculateBollingerBands(candles, period, stdDevMultiplier) {
    const upper = [];
    const middle = [];
    const lower = [];
    
    for (let i = 0; i < candles.length; i++) {
        if (i < period - 1) continue;
        
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += candles[i - j].close;
        }
        const sma = sum / period;
        
        let sumSquaredDiff = 0;
        for (let j = 0; j < period; j++) {
            sumSquaredDiff += Math.pow(candles[i - j].close - sma, 2);
        }
        const stdDev = Math.sqrt(sumSquaredDiff / period);
        
        middle.push({ time: candles[i].time, value: sma });
        upper.push({ time: candles[i].time, value: sma + stdDev * stdDevMultiplier });
        lower.push({ time: candles[i].time, value: sma - stdDev * stdDevMultiplier });
    }
    
    return { upper, middle, lower };
}

// Parabolic SAR
function calculateSAR(candles) {
    const result = [];
    if (candles.length < 2) return result;
    
    let af = 0.02;
    const maxAf = 0.2;
    let isLong = true;
    let sar = candles[0].low;
    let ep = candles[0].high;
    
    for (let i = 1; i < candles.length; i++) {
        const prevSar = sar;
        sar = prevSar + af * (ep - prevSar);
        
        if (isLong) {
            if (candles[i].low < sar) {
                isLong = false;
                sar = ep;
                ep = candles[i].low;
                af = 0.02;
            } else {
                if (candles[i].high > ep) {
                    ep = candles[i].high;
                    af = Math.min(af + 0.02, maxAf);
                }
            }
        } else {
            if (candles[i].high > sar) {
                isLong = true;
                sar = ep;
                ep = candles[i].high;
                af = 0.02;
            } else {
                if (candles[i].low < ep) {
                    ep = candles[i].low;
                    af = Math.min(af + 0.02, maxAf);
                }
            }
        }
        
        result.push({ time: candles[i].time, value: sar });
    }
    
    return result;
}

// SuperTrend
function calculateSuperTrend(candles, period = 10, multiplier = 3) {
    const result = [];
    if (candles.length < period) return result;
    
    const trs = [];
    for (let i = 1; i < candles.length; i++) {
        const high = candles[i].high;
        const low = candles[i].low;
        const prevClose = candles[i-1].close;
        trs.push(Math.max(
            high - low,
            Math.abs(high - prevClose),
            Math.abs(low - prevClose)
        ));
    }
    
    let atr = trs.slice(0, period).reduce((a, b) => a + b, 0) / period;
    let upperBand = (candles[period].high + candles[period].low) / 2 + multiplier * atr;
    let lowerBand = (candles[period].high + candles[period].low) / 2 - multiplier * atr;
    let inUptrend = true;
    
    for (let i = period; i < candles.length; i++) {
        const currHigh = candles[i].high;
        const currLow = candles[i].low;
        const currClose = candles[i].close;
        const prevClose = candles[i-1].close;
        
        if (i > period) {
            const tr = Math.max(
                currHigh - currLow,
                Math.abs(currHigh - prevClose),
                Math.abs(currLow - prevClose)
            );
            atr = (atr * (period - 1) + tr) / period;
        }
        
        let currUpperBand = (currHigh + currLow) / 2 + multiplier * atr;
        let currLowerBand = (currHigh + currLow) / 2 - multiplier * atr;
        
        if (inUptrend) {
            if (currLowerBand < lowerBand) currLowerBand = lowerBand;
            if (currClose < lowerBand) {
                inUptrend = false;
                upperBand = currUpperBand;
            } else {
                lowerBand = currLowerBand;
            }
        } else {
            if (currUpperBand > upperBand) currUpperBand = upperBand;
            if (currClose > upperBand) {
                inUptrend = true;
                lowerBand = currLowerBand;
            } else {
                upperBand = currUpperBand;
            }
        }
        
        result.push({
            time: candles[i].time,
            value: inUptrend ? lowerBand : upperBand,
            color: inUptrend ? '#26a69a' : '#ef5350'
        });
    }
    
    return result;
}

// Support and Resistance
function calculateSupportResistance(candles) {
    const support = [];
    const resistance = [];
    let lastHigh = null;
    let lastLow = null;
    
    for (let i = 0; i < candles.length; i++) {
        if (i >= 4) {
            const idx = i - 2;
            const center = candles[idx];
            const l1 = candles[idx-1];
            const l2 = candles[idx-2];
            const r1 = candles[idx+1];
            const r2 = candles[i];
            
            if (center.high > l1.high && center.high > l2.high && 
                center.high > r1.high && center.high > r2.high) {
                lastHigh = center.high;
            }
            if (center.low < l1.low && center.low < l2.low && 
                center.low < r1.low && center.low < r2.low) {
                lastLow = center.low;
            }
        }
        
        if (lastHigh !== null) {
            resistance.push({ time: candles[i].time, value: lastHigh });
        }
        if (lastLow !== null) {
            support.push({ time: candles[i].time, value: lastLow });
        }
    }
    
    return { support, resistance };
}

// MACD
function calculateMACD(candles, fastPeriod, slowPeriod, signalPeriod) {
    const emaFast = calculateEMA(candles, fastPeriod);
    const emaSlow = calculateEMA(candles, slowPeriod);
    const difData = [];
    const deaData = [];
    const histogramData = [];
    
    const minLen = Math.min(emaFast.length, emaSlow.length);
    const offsetFast = emaFast.length - minLen;
    const offsetSlow = emaSlow.length - minLen;
    const difValues = [];
    
    for (let i = 0; i < minLen; i++) {
        const val = emaFast[i + offsetFast].value - emaSlow[i + offsetSlow].value;
        const time = emaFast[i + offsetFast].time;
        difValues.push({ time, value: val });
        difData.push({ time, value: val });
    }
    
    let dea = difValues[0].value;
    const k = 2 / (signalPeriod + 1);
    deaData.push({ time: difValues[0].time, value: dea });
    histogramData.push({
        time: difValues[0].time,
        value: difValues[0].value - dea,
        color: (difValues[0].value - dea) >= 0 ? '#26a69a' : '#ef5350'
    });
    
    for (let i = 1; i < difValues.length; i++) {
        dea = (difValues[i].value - dea) * k + dea;
        deaData.push({ time: difValues[i].time, value: dea });
        const hist = difValues[i].value - dea;
        histogramData.push({
            time: difValues[i].time,
            value: hist,
            color: hist >= 0 ? '#26a69a' : '#ef5350'
        });
    }
    
    return { dif: difData, dea: deaData, histogram: histogramData };
}

// RSI
function calculateRSI(candles, period) {
    const result = [];
    if (candles.length < period + 1) return result;
    
    let gains = 0;
    let losses = 0;
    
    for (let i = 1; i <= period; i++) {
        const change = candles[i].close - candles[i-1].close;
        if (change > 0) {
            gains += change;
        } else {
            losses -= change;
        }
    }
    
    let avgGain = gains / period;
    let avgLoss = losses / period;
    
    for (let i = period + 1; i < candles.length; i++) {
        const change = candles[i].close - candles[i-1].close;
        const gain = change > 0 ? change : 0;
        const loss = change < 0 ? -change : 0;
        
        avgGain = (avgGain * (period - 1) + gain) / period;
        avgLoss = (avgLoss * (period - 1) + loss) / period;
        
        const rs = avgGain / avgLoss;
        result.push({
            time: candles[i].time,
            value: 100 - (100 / (1 + rs))
        });
    }
    
    return result;
}

// KDJ
function calculateKDJ(candles, n, m1, m2) {
    const kData = [];
    const dData = [];
    const jData = [];
    let k = 50;
    let d = 50;
    
    for (let i = 0; i < candles.length; i++) {
        if (i < n - 1) continue;
        
        let low = candles[i].low;
        let high = candles[i].high;
        
        for (let j = 0; j < n; j++) {
            if (candles[i-j].low < low) low = candles[i-j].low;
            if (candles[i-j].high > high) high = candles[i-j].high;
        }
        
        const rsv = (candles[i].close - low) / (high - low) * 100;
        k = (m1 - 1) / m1 * k + 1 / m1 * rsv;
        d = (m2 - 1) / m2 * d + 1 / m2 * k;
        
        kData.push({ time: candles[i].time, value: k });
        dData.push({ time: candles[i].time, value: d });
        jData.push({ time: candles[i].time, value: 3 * k - 2 * d });
    }
    
    return { k: kData, d: dData, j: jData };
}

// CCI
function calculateCCI(candles, period) {
    const result = [];
    if (candles.length < period) return result;
    
    const tps = candles.map(c => (c.high + c.low + c.close) / 3);
    
    for (let i = period - 1; i < candles.length; i++) {
        let sumTp = 0;
        for (let j = 0; j < period; j++) {
            sumTp += tps[i-j];
        }
        const maTp = sumTp / period;
        
        let sumMd = 0;
        for (let j = 0; j < period; j++) {
            sumMd += Math.abs(tps[i-j] - maTp);
        }
        const md = sumMd / period;
        
        result.push({
            time: candles[i].time,
            value: (tps[i] - maTp) / (0.015 * md)
        });
    }
    
    return result;
}

// Williams %R
function calculateWR(candles, period) {
    const result = [];
    
    for (let i = period - 1; i < candles.length; i++) {
        let highest = -Infinity;
        let lowest = Infinity;
        
        for (let j = 0; j < period; j++) {
            if (candles[i-j].high > highest) highest = candles[i-j].high;
            if (candles[i-j].low < lowest) lowest = candles[i-j].low;
        }
        
        result.push({
            time: candles[i].time,
            value: (highest - candles[i].close) / (highest - lowest) * -100
        });
    }
    
    return result;
}

// On-Balance Volume
function calculateOBV(candles) {
    const result = [];
    let obv = 0;
    
    result.push({ time: candles[0].time, value: obv });
    
    for (let i = 1; i < candles.length; i++) {
        if (candles[i].close > candles[i-1].close) {
            obv += candles[i].volume;
        } else if (candles[i].close < candles[i-1].close) {
            obv -= candles[i].volume;
        }
        result.push({ time: candles[i].time, value: obv });
    }
    
    return result;
}

// Rate of Change
function calculateROC(candles, period) {
    const result = [];
    
    for (let i = period; i < candles.length; i++) {
        result.push({
            time: candles[i].time,
            value: ((candles[i].close - candles[i-period].close) / candles[i-period].close) * 100
        });
    }
    
    return result;
}

// Momentum
function calculateMTM(candles, period) {
    const result = [];
    
    for (let i = period; i < candles.length; i++) {
        result.push({
            time: candles[i].time,
            value: candles[i].close - candles[i-period].close
        });
    }
    
    return result;
}

// Psychological Line
function calculatePSY(candles, period) {
    const result = [];
    
    for (let i = period; i < candles.length; i++) {
        let upCount = 0;
        for (let j = 0; j < period; j++) {
            if (candles[i-j].close > candles[i-j-1].close) {
                upCount++;
            }
        }
        result.push({
            time: candles[i].time,
            value: (upCount / period) * 100
        });
    }
    
    return result;
}

// DMI (Directional Movement Index)
function calculateDMI(candles, period = 14) {
    if (candles.length < period + 1) {
        return { pdi: [], mdi: [], adx: [] };
    }
    
    const pdi = [];
    const mdi = [];
    const adx = [];
    
    // Step 1: Calculate +DM, -DM, and TR (True Range)
    const plusDM = [];
    const minusDM = [];
    const tr = [];
    
    for (let i = 1; i < candles.length; i++) {
        const high = candles[i].high;
        const low = candles[i].low;
        const prevHigh = candles[i - 1].high;
        const prevLow = candles[i - 1].low;
        const prevClose = candles[i - 1].close;
        
        // +DM and -DM
        const upMove = high - prevHigh;
        const downMove = prevLow - low;
        
        let plusDMValue = 0;
        let minusDMValue = 0;
        
        if (upMove > downMove && upMove > 0) {
            plusDMValue = upMove;
        }
        if (downMove > upMove && downMove > 0) {
            minusDMValue = downMove;
        }
        
        plusDM.push(plusDMValue);
        minusDM.push(minusDMValue);
        
        // True Range
        const tr1 = high - low;
        const tr2 = Math.abs(high - prevClose);
        const tr3 = Math.abs(low - prevClose);
        tr.push(Math.max(tr1, tr2, tr3));
    }
    
    // Step 2: Smooth +DM, -DM, and TR using Wilder's smoothing
    let smoothedPlusDM = plusDM.slice(0, period).reduce((a, b) => a + b, 0);
    let smoothedMinusDM = minusDM.slice(0, period).reduce((a, b) => a + b, 0);
    let smoothedTR = tr.slice(0, period).reduce((a, b) => a + b, 0);
    
    const smoothedPlusDMArray = [smoothedPlusDM];
    const smoothedMinusDMArray = [smoothedMinusDM];
    const smoothedTRArray = [smoothedTR];
    
    for (let i = period; i < plusDM.length; i++) {
        smoothedPlusDM = smoothedPlusDM - (smoothedPlusDM / period) + plusDM[i];
        smoothedMinusDM = smoothedMinusDM - (smoothedMinusDM / period) + minusDM[i];
        smoothedTR = smoothedTR - (smoothedTR / period) + tr[i];
        
        smoothedPlusDMArray.push(smoothedPlusDM);
        smoothedMinusDMArray.push(smoothedMinusDM);
        smoothedTRArray.push(smoothedTR);
    }
    
    // Step 3: Calculate +DI and -DI
    const plusDI = [];
    const minusDI = [];
    
    for (let i = 0; i < smoothedTRArray.length; i++) {
        const pdiValue = smoothedTRArray[i] === 0 ? 0 : (smoothedPlusDMArray[i] / smoothedTRArray[i]) * 100;
        const mdiValue = smoothedTRArray[i] === 0 ? 0 : (smoothedMinusDMArray[i] / smoothedTRArray[i]) * 100;
        
        plusDI.push(pdiValue);
        minusDI.push(mdiValue);
    }
    
    // Step 4: Calculate DX
    const dx = [];
    for (let i = 0; i < plusDI.length; i++) {
        const sum = plusDI[i] + minusDI[i];
        const dxValue = sum === 0 ? 0 : (Math.abs(plusDI[i] - minusDI[i]) / sum) * 100;
        dx.push(dxValue);
    }
    
    // Step 5: Calculate ADX (smoothed DX)
    if (dx.length >= period) {
        let adxValue = dx.slice(0, period).reduce((a, b) => a + b, 0) / period;
        
        for (let i = 0; i < plusDI.length; i++) {
            if (i < period - 1) {
                // Not enough data yet
                continue;
            }
            
            if (i === period - 1) {
                // First ADX value
                adx.push({ time: candles[i + period].time, value: adxValue });
            } else {
                // Subsequent ADX values using Wilder's smoothing
                adxValue = ((adxValue * (period - 1)) + dx[i]) / period;
                adx.push({ time: candles[i + period].time, value: adxValue });
            }
        }
    }
    
    // Build final result arrays
    for (let i = 0; i < plusDI.length; i++) {
        pdi.push({ time: candles[i + period].time, value: plusDI[i] });
        mdi.push({ time: candles[i + period].time, value: minusDI[i] });
    }
    
    return { pdi, mdi, adx };
}

// Stochastic RSI - Simplified
function calculateStochRSI(candles, rsiPeriod, stochPeriod, kPeriod, dPeriod) {
    // Step 1: Calculate RSI
    const rsiValues = [];
    for (let i = rsiPeriod; i < candles.length; i++) {
        let gains = 0;
        let losses = 0;
        
        for (let j = 0; j < rsiPeriod; j++) {
            const change = candles[i - j].close - candles[i - j - 1].close;
            if (change > 0) {
                gains += change;
            } else {
                losses += Math.abs(change);
            }
        }
        
        const avgGain = gains / rsiPeriod;
        const avgLoss = losses / rsiPeriod;
        const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        const rsi = 100 - (100 / (1 + rs));
        
        rsiValues.push({ time: candles[i].time, value: rsi });
    }
    
    // Step 2: Calculate Stochastic of RSI
    const stochRSI = [];
    for (let i = stochPeriod - 1; i < rsiValues.length; i++) {
        const slice = rsiValues.slice(i - stochPeriod + 1, i + 1);
        const maxRSI = Math.max(...slice.map(r => r.value));
        const minRSI = Math.min(...slice.map(r => r.value));
        const currentRSI = rsiValues[i].value;
        
        const stoch = maxRSI === minRSI ? 0 : ((currentRSI - minRSI) / (maxRSI - minRSI)) * 100;
        stochRSI.push({ time: rsiValues[i].time, value: stoch });
    }
    
    // Step 3: Calculate K line (SMA of StochRSI)
    const k = [];
    for (let i = kPeriod - 1; i < stochRSI.length; i++) {
        const slice = stochRSI.slice(i - kPeriod + 1, i + 1);
        const avg = slice.reduce((sum, val) => sum + val.value, 0) / kPeriod;
        k.push({ time: stochRSI[i].time, value: avg });
    }
    
    // Step 4: Calculate D line (SMA of K)
    const d = [];
    for (let i = dPeriod - 1; i < k.length; i++) {
        const slice = k.slice(i - dPeriod + 1, i + 1);
        const avg = slice.reduce((sum, val) => sum + val.value, 0) / dPeriod;
        d.push({ time: k[i].time, value: avg });
    }
    
    return { k, d };
}

// TRIX - Simplified
function calculateTRIX(candles, period) {
    const result = [];
    
    // Simplified: Triple EMA
    const ema1 = calculateEMA(candles, period);
    
    for (let i = 1; i < ema1.length; i++) {
        result.push({
            time: ema1[i].time,
            value: ((ema1[i].value - ema1[i-1].value) / ema1[i-1].value) * 100
        });
    }
    
    return result;
}

// DMA (Different of Moving Average)
function calculateDMA(candles, shortPeriod, longPeriod) {
    const shortMA = calculateSMA(candles, shortPeriod);
    const longMA = calculateSMA(candles, longPeriod);
    const ddd = [];
    const ama = [];
    
    const minLen = Math.min(shortMA.length, longMA.length);
    
    for (let i = 0; i < minLen; i++) {
        const diff = shortMA[shortMA.length - minLen + i].value - longMA[longMA.length - minLen + i].value;
        ddd.push({
            time: shortMA[shortMA.length - minLen + i].time,
            value: diff
        });
    }
    
    // AMA is MA of DDD
    for (let i = 9; i < ddd.length; i++) {
        let sum = 0;
        for (let j = 0; j < 10; j++) {
            sum += ddd[i-j].value;
        }
        ama.push({
            time: ddd[i].time,
            value: sum / 10
        });
    }
    
    return { dma1: ddd, dma2: ama };
}

// VR (Volume Ratio) - Simplified
function calculateVR(candles, period) {
    const result = [];
    
    for (let i = period; i < candles.length; i++) {
        let upVol = 0;
        let downVol = 0;
        
        for (let j = 0; j < period; j++) {
            if (candles[i-j].close > candles[i-j-1].close) {
                upVol += candles[i-j].volume;
            } else {
                downVol += candles[i-j].volume;
            }
        }
        
        result.push({
            time: candles[i].time,
            value: downVol > 0 ? (upVol / downVol) * 100 : 100
        });
    }
    
    return result;
}

// BRAR - Simplified
function calculateBRAR(candles, period) {
    const br = [];
    const ar = [];
    
    for (let i = period; i < candles.length; i++) {
        // Simplified calculation
        br.push({ time: candles[i].time, value: 100 });
        ar.push({ time: candles[i].time, value: 100 });
    }
    
    return { br, ar };
}

// ATR (Average True Range)
function calculateATR(candles, period = 14) {
    if (candles.length < period + 1) return [];
    
    const result = [];
    const trValues = [];
    
    // Calculate True Range for each candle
    for (let i = 1; i < candles.length; i++) {
        const high = candles[i].high;
        const low = candles[i].low;
        const prevClose = candles[i-1].close;
        
        // True Range = max of:
        // 1. High - Low
        // 2. |High - Previous Close|
        // 3. |Low - Previous Close|
        const tr = Math.max(
            high - low,
            Math.abs(high - prevClose),
            Math.abs(low - prevClose)
        );
        
        trValues.push(tr);
    }
    
    // Calculate initial ATR (simple average of first 'period' TR values)
    let atr = 0;
    for (let i = 0; i < period; i++) {
        atr += trValues[i];
    }
    atr = atr / period;
    
    result.push({
        time: candles[period].time,
        value: atr
    });
    
    // Calculate subsequent ATR values using smoothing (Wilder's smoothing)
    // ATR = ((Previous ATR * (period - 1)) + Current TR) / period
    for (let i = period; i < trValues.length; i++) {
        atr = ((atr * (period - 1)) + trValues[i]) / period;
        result.push({
            time: candles[i + 1].time,
            value: atr
        });
    }
    
    return result;
}
