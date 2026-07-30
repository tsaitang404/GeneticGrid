<template>
  <section class="trading-tools-panel">
    <div class="tools-tabs">
      <button :class="['tab-btn', { active: activeTab === 'spot' }]" @click="activeTab = 'spot'">
        💱 现货交易
      </button>
      <button :class="['tab-btn', { active: activeTab === 'contract' }]" @click="activeTab = 'contract'">
        📈 合约交易
      </button>
      <button :class="['tab-btn', { active: activeTab === 'option' }]" @click="activeTab = 'option'">
        🎯 期权交易
      </button>
      <button :class="['tab-btn', { active: activeTab === 'strategy' }]" @click="activeTab = 'strategy'">
        🤖 策略交易
      </button>
      <button :class="['tab-btn', { active: activeTab === 'position' }]" @click="activeTab = 'position'">
        📊 仓位管理
      </button>
    </div>

    <!-- ===== 现货交易 ===== -->
    <div v-show="activeTab === 'spot'" class="tab-content">
      <template v-if="!isLoggedIn">
        <div class="login-prompt">
          <div class="prompt-icon">🔑</div>
          <div class="prompt-text">请先登陆</div>
          <button class="btn primary" @click="$emit('open-account')">前往登陆</button>
        </div>
      </template>
      <template v-else-if="!tradePerm">
        <div class="no-perm">⚠️ 当前 API Key 无交易权限</div>
      </template>
      <template v-else>
        <div class="trade-form">
          <div class="form-row">
            <label>交易对</label>
            <SymbolSelector v-model="spotForm.symbol" :symbols="spotSymbols" size="small" />
          </div>
          <div class="side-group">
            <button :class="['side-btn', { active: spotForm.side === 'buy' }]" @click="spotForm.side = 'buy'">买入</button>
            <button :class="['side-btn', 'sell', { active: spotForm.side === 'sell' }]" @click="spotForm.side = 'sell'">卖出</button>
          </div>
          <div class="form-row">
            <label>类型</label>
            <div class="type-group">
              <button :class="['type-btn', { active: spotForm.ordType === 'limit' }]" @click="spotForm.ordType = 'limit'">限价单</button>
              <button :class="['type-btn', { active: spotForm.ordType === 'market' }]" @click="spotForm.ordType = 'market'">市价单</button>
            </div>
          </div>
          <div v-if="spotForm.ordType === 'limit'" class="form-row">
            <label>价格 (USDT)</label>
            <input v-model.number="spotForm.px" type="number" step="0.1" class="input" />
          </div>
          <div class="form-row">
            <label>数量</label>
            <div class="qty-row">
              <input v-model.number="spotForm.sz" type="number" step="0.0001" class="input" />
              <span class="unit">{{ spotUnit }}</span>
            </div>
          </div>
          <div class="qty-mode-group">
            <button :class="['qty-mode-btn', { active: spotForm.szMode === 'base' }]" @click="spotForm.szMode = 'base'">币数</button>
            <button :class="['qty-mode-btn', { active: spotForm.szMode === 'quote' }]" @click="spotForm.szMode = 'quote'">金额</button>
          </div>
          <div class="balance-row" v-if="balance">
            <span>可用: {{ availSpot }}</span>
          </div>
          <button class="btn primary trade-submit" @click="showConfirm = true">
            {{ spotForm.side === 'buy' ? '买入' : '卖出' }} {{ spotForm.symbol }}
          </button>
        </div>
      </template>
    </div>

    <!-- ===== 合约交易 ===== -->
    <div v-show="activeTab === 'contract'" class="tab-content">
      <template v-if="!isLoggedIn">
        <div class="login-prompt">
          <div class="prompt-icon">🔑</div>
          <div class="prompt-text">请先登陆</div>
          <button class="btn primary" @click="$emit('open-account')">前往登陆</button>
        </div>
      </template>
      <template v-else-if="!tradePerm">
        <div class="no-perm">⚠️ 当前 API Key 无交易权限</div>
      </template>
      <template v-else>
        <div class="trade-form">
          <div class="form-row">
            <label>交易对</label>
            <SymbolSelector v-model="contractForm.symbol" :symbols="contractSymbols" size="small" />
          </div>
          <div class="side-group">
            <button :class="['side-btn', { active: contractForm.side === 'long' }]" @click="contractForm.side = 'long'">做多</button>
            <button :class="['side-btn', 'sell', { active: contractForm.side === 'short' }]" @click="contractForm.side = 'short'">做空</button>
          </div>
          <div class="form-row">
            <label>保证金模式</label>
            <div class="type-group">
              <button :class="['type-btn', { active: contractForm.tdMode === 'cross' }]" @click="contractForm.tdMode = 'cross'">全仓</button>
              <button :class="['type-btn', { active: contractForm.tdMode === 'isolated' }]" @click="contractForm.tdMode = 'isolated'">逐仓</button>
            </div>
          </div>
          <div class="form-row">
            <label>杠杆 {{ contractForm.lever }}x</label>
            <input v-model.number="contractForm.lever" type="range" min="1" max="125" class="lever-slider" />
          </div>
          <div class="form-row">
            <label>数量</label>
            <div class="qty-row">
              <input v-model.number="contractForm.sz" type="number" step="0.001" class="input" />
              <span class="unit">{{ contractUnit }}</span>
            </div>
          </div>
          <div class="qty-mode-group">
            <button :class="['qty-mode-btn', { active: contractForm.szMode === 'coin' }]" @click="contractForm.szMode = 'coin'">币数</button>
            <button :class="['qty-mode-btn', { active: contractForm.szMode === 'contract' }]" @click="contractForm.szMode = 'contract'">张数</button>
          </div>
          <div class="margin-preview" v-if="spotPrice && contractForm.sz">
            预计保证金: <b>{{ estMargin }}</b>
          </div>
          <button class="btn primary trade-submit" @click="showConfirm = true">
            {{ contractForm.side === 'long' ? '做多' : '做空' }} {{ contractForm.symbol }}
          </button>
        </div>
      </template>
    </div>

    <!-- ===== 期权交易 ===== -->
    <div v-show="activeTab === 'option'" class="tab-content">
      <template v-if="!isLoggedIn">
        <div class="login-prompt">
          <div class="prompt-icon">🔑</div>
          <div class="prompt-text">请先登陆</div>
          <button class="btn primary" @click="$emit('open-account')">前往登陆</button>
        </div>
      </template>
      <template v-else-if="!tradePerm">
        <div class="no-perm">⚠️ 当前 API Key 无交易权限</div>
      </template>
      <template v-else>
        <div class="trade-form">
          <div class="form-row">
            <label>标的资产</label>
            <select v-model="optionForm.uly" class="input" @change="fetchOptionInstruments">
              <option v-for="u in optionUlyList" :key="u" :value="u">{{ u }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>到期日</label>
            <select v-model="optionForm.expTime" class="input" @change="onOptionChange">
              <option v-for="e in sortedExpiries" :key="e.value" :value="e.value">{{ e.label }}</option>
            </select>
          </div>
          <div class="option-chain">
            <div class="chain-header">
              <span class="col-strike">行权价</span>
              <span class="col-call">看涨 (C)</span>
              <span class="col-put">看跌 (P)</span>
            </div>
            <div v-for="row in optionChainRows" :key="row.strike" class="chain-row" :class="{ selected: selectedStrike === row.strike }">
              <span class="col-strike">{{ row.strike }}</span>
              <span class="col-call" :class="{ active: optionForm.optType === 'C' && selectedStrike === row.strike }">
                <button v-if="row.call" class="opt-btn" @click="selectOption(row.call, 'C')">
                  <span class="opt-bid">{{ row.call.bid || '-' }}</span>
                  <span class="opt-ask">{{ row.call.ask || '-' }}</span>
                </button>
                <span v-else class="no-opt">-</span>
              </span>
              <span class="col-put" :class="{ active: optionForm.optType === 'P' && selectedStrike === row.strike }">
                <button v-if="row.put" class="opt-btn" @click="selectOption(row.put, 'P')">
                  <span class="opt-bid">{{ row.put.bid || '-' }}</span>
                  <span class="opt-ask">{{ row.put.ask || '-' }}</span>
                </button>
                <span v-else class="no-opt">-</span>
              </span>
            </div>
          </div>
          <div v-if="selectedOption" class="selected-info">
            已选: {{ selectedOption.inst_id }}
            <span v-if="optionTicker" class="ticker-info">
              最新价: {{ optionTicker.last }} IV: {{ optionTicker.iv }}
            </span>
          </div>
          <div class="side-group">
            <button :class="['side-btn', { active: optionForm.side === 'buy' }]" @click="optionForm.side = 'buy'">买入</button>
            <button :class="['side-btn', 'sell', { active: optionForm.side === 'sell' }]" @click="optionForm.side = 'sell'">卖出</button>
          </div>
          <div class="form-row">
            <label>类型</label>
            <div class="type-group">
              <button :class="['type-btn', { active: optionForm.ordType === 'limit' }]" @click="optionForm.ordType = 'limit'">限价单</button>
              <button :class="['type-btn', { active: optionForm.ordType === 'market' }]" @click="optionForm.ordType = 'market'">市价单</button>
            </div>
          </div>
          <div v-if="optionForm.ordType === 'limit'" class="form-row">
            <label>价格 (USDT)</label>
            <input v-model.number="optionForm.px" type="number" step="0.1" class="input" />
          </div>
          <div class="form-row">
            <label>数量 (张)</label>
            <input v-model.number="optionForm.sz" type="number" step="1" min="1" class="input" />
          </div>
          <button class="btn primary trade-submit" :disabled="!selectedOption" @click="showConfirm = true">
            {{ optionForm.side === 'buy' ? '买入' : '卖出' }} 期权
          </button>
        </div>
      </template>
    </div>

    <!-- ===== 仓位管理 ===== (与之前相同) -->
    <div v-show="activeTab === 'position'" class="tab-content">
      <div v-if="!isLoggedIn" class="login-prompt">
        <div class="prompt-icon">🔑</div>
        <div class="prompt-text">请先登陆以查看仓位信息</div>
        <button class="btn primary" @click="$emit('open-account')">前往登陆</button>
      </div>
      <template v-else>
        <div class="position-toolbar">
          <div class="position-section">
            <h4>持有仓位</h4>
            <span v-if="filteredPositions.length" class="total-count">共 {{ filteredPositions.length }} 个</span>
          </div>
          <div class="toolbar-actions">
            <div class="search-box">
              <input v-model="filterSymbol" placeholder="搜索币对" class="search-input" />
            </div>
            <button class="refresh-btn" :disabled="posLoading" @click="loadPositions">
              {{ posLoading ? '加载中...' : '🔄 刷新' }}
            </button>
          </div>
        </div>
        <div v-if="filteredPositions.length" class="summary-bar">
          <div class="summary-item"><span class="label">总名义价值</span><span class="value">${{ totalNotional }}</span></div>
          <div class="summary-item"><span class="label">总未实现盈亏</span><span :class="['value', totalUnrealizedPnl >= 0 ? 'profit' : 'loss']">{{ totalUnrealizedPnl >= 0 ? '+' : '' }}{{ totalUnrealizedPnl }}</span></div>
          <div class="summary-item"><span class="label">多头</span><span class="value long-count">{{ longCount }}</span></div>
          <div class="summary-item"><span class="label">空头</span><span class="value short-count">{{ shortCount }}</span></div>
          <div class="summary-item"><span class="label">现货</span><span class="value spot-count">{{ spotCount }}</span></div>
        </div>
        <div v-if="posLoading" class="loading">加载仓位中...</div>
        <div v-else-if="posError" class="error">{{ posError }}</div>
        <div v-else-if="filteredPositions.length === 0" class="empty">{{ filterSymbol ? '没有匹配的仓位' : '暂无持仓' }}</div>
        <div v-else class="position-list">
          <div v-for="pos in filteredPositions" :key="pos.symbol + '-' + pos.side"
            :class="['position-card', { expanded: expandedSymbol === pos.symbol + '-' + pos.side }]"
            @click="toggleExpand(pos.symbol + '-' + pos.side)">
            <div class="pos-header">
              <div class="pos-title"><h5>{{ pos.symbol }}</h5><span :class="['pos-side', pos.side?.toLowerCase()]">{{ pos.side }}</span></div>
              <div class="pos-pnl">
                <span :class="+pos.unrealizedPnl >= 0 ? 'profit' : 'loss'">{{ +pos.unrealizedPnl >= 0 ? '+' : '' }}{{ formatNumber(pos.unrealizedPnl) }}</span>
                <span class="pnl-pct" :class="+pos.unrealizedPnl >= 0 ? 'profit' : 'loss'">{{ (+pos.unrealizedPnlRatio * 100).toFixed(2) }}%</span>
              </div>
            </div>
            <div class="pos-row">
              <div class="pos-metric"><span class="label">数量</span><span class="value">{{ formatNumber(pos.positionQty) }}</span></div>
              <div class="pos-metric"><span class="label">标记价格</span><span class="value">${{ formatNumber(pos.markPrice) }}</span></div>
              <div v-if="pos.side === 'spot' && pos.avgCostPrice" class="pos-metric"><span class="label">建仓均价</span><span class="value">${{ formatNumber(pos.avgCostPrice) }}</span></div>
              <div v-else class="pos-metric"><span class="label">杠杆</span><span class="value">{{ pos.leverage }}x</span></div>
            </div>
            <div v-if="expandedSymbol === pos.symbol + '-' + pos.side" class="pos-details">
              <div class="detail-row">
                <div class="detail-item"><span class="label">名义价值</span><span class="value">${{ formatNumber(pos.notionalValue) }}</span></div>
                <div class="detail-item"><span class="label">保证金模式</span><span class="value">{{ pos.mgnMode === 'cross' ? '全仓' : '逐仓' }}</span></div>
              </div>
              <div class="detail-row">
                <div class="detail-item"><span class="label">可平数量</span><span class="value">{{ formatNumber(pos.available) }}</span></div>
                <div class="detail-item"><span class="label">冻结数量</span><span class="value frozen">{{ formatNumber(pos.frozenQty) }}</span></div>
              </div>
              <div class="detail-row">
                <div class="detail-item"><span class="label">未实现盈亏率</span><span :class="['value', +pos.unrealizedPnlRatio >= 0 ? 'profit' : 'loss']">{{ (+pos.unrealizedPnlRatio * 100).toFixed(4) }}%</span></div>
                <div class="detail-item"><span class="label">更新时间</span><span class="value">{{ formatTime(pos.timestamp) }}</span></div>
              </div>
            </div>
            <div v-if="pos.side === 'spot' && !pos.avgCostPrice" class="pos-note">转入资产，无建仓成本</div>
            <div class="pos-expand-hint">{{ expandedSymbol === pos.symbol + '-' + pos.side ? '收起' : '查看详情' }}</div>
          </div>
        </div>
      </template>
    </div>

    <!-- ===== 策略交易 ===== -->
    <div v-show="activeTab === 'strategy'" class="tab-content">
      <div class="strategy-sub-tabs">
        <button :class="['sub-tab-btn', { active: strategyMode === 'dca' }]" @click="strategyMode = 'dca'">📅 定投 DCA</button>
        <button :class="['sub-tab-btn', { active: strategyMode === 'grid' }]" @click="strategyMode = 'grid'">🧱 网格交易</button>
        <button :class="['sub-tab-btn', { active: strategyMode === 'trailing_stop' }]" @click="strategyMode = 'trailing_stop'">🎯 追踪止损</button>
        <button :class="['sub-tab-btn', { active: strategyMode === 'iceberg' }]" @click="strategyMode = 'iceberg'">🧊 冰山订单</button>
        <button :class="['sub-tab-btn', { active: strategyMode === 'twap' }]" @click="strategyMode = 'twap'">⏱ TWAP</button>
        <button :class="['sub-tab-btn', 'disabled']" disabled title="即将上线">📈 策略回测</button>
        <button :class="['sub-tab-btn', 'disabled']" disabled title="即将上线">🛡️ 风险控制</button>
      </div>

      <!-- 网格交易 -->
      <div v-show="strategyMode === 'grid'" class="strategy-content">
        <div class="form-grid">
          <div class="form-group"><label>交易对</label><input v-model="gridForm.symbol" placeholder="如 BTCUSDT" /></div>
          <div class="form-group"><label>网格数量</label><input v-model.number="gridForm.grids" type="number" min="2" max="200" /></div>
          <div class="form-group"><label>下限价格</label><input v-model.number="gridForm.lower" type="number" min="0" step="0.01" /></div>
          <div class="form-group"><label>上限价格</label><input v-model.number="gridForm.upper" type="number" min="0" step="0.01" /></div>
          <div class="form-group"><label>投资金额</label><input v-model.number="gridForm.invest" type="number" min="0" step="0.01" /></div>
          <div class="form-group"><label>风格</label><select v-model="gridForm.mode"><option value="arithmetic">等差</option><option value="geometric">等比</option></select></div>
        </div>
        <div class="preview-info">
          <div class="preview-item"><span>预计每网格资金</span><b>{{ gridFund.toFixed(4) }}</b></div>
          <div class="preview-item"><span>预计价格步长</span><b>{{ stepPreview }}</b></div>
        </div>
        <div class="form-actions"><button class="btn primary" @click="createGrid">创建网格</button></div>
        <p class="tip">💡 当前为原型占位，不会触发真实交易</p>
      </div>

      <!-- DCA 定投 -->
      <div v-show="strategyMode === 'dca'" class="strategy-content">
        <div class="form-grid">
          <div class="form-group"><label>交易对</label>
            <SymbolSelector v-model="dcaForm.symbol" :symbols="spotSymbols" size="small" />
          </div>
          <div class="form-group"><label>每期投入 (USDT)</label><input v-model.number="dcaForm.amount" type="number" min="1" step="1" class="input" /></div>
          <div class="form-group"><label>执行间隔</label>
            <select v-model="dcaForm.intervalHours" class="input">
              <option :value="1">每小时</option>
              <option :value="4">每 4 小时</option>
              <option :value="8">每 8 小时</option>
              <option :value="24">每天</option>
              <option :value="168">每周</option>
            </select>
          </div>
          <div class="form-group"><label>最大执行次数</label>
            <select v-model.number="dcaForm.maxExecutions" class="input">
              <option :value="0">不限</option>
              <option :value="12">12 次</option>
              <option :value="30">30 次</option>
              <option :value="100">100 次</option>
            </select>
          </div>
          <div class="form-group"><label>策略名称（可选）</label><input v-model="dcaForm.name" placeholder="如 BTC 定投" class="input" /></div>
        </div>
        <div class="preview-info">
          <div class="preview-item"><span>每期金额</span><b>{{ dcaForm.amount }} USDT</b></div>
          <div class="preview-item"><span>执行计划</span><b>{{ dcaSummary }}</b></div>
        </div>
        <div class="form-actions">
          <button class="btn primary" :disabled="dcaSubmitting" @click="createDCA">{{ dcaSubmitting ? '创建中...' : '创建 DCA 策略' }}</button>
        </div>
        <div v-if="dcaResult" class="order-result">✅ 策略已创建 (ID: {{ dcaResult.id }})</div>
        <div v-if="dcaError" class="error">{{ dcaError }}</div>
        <p class="tip">💡 DCA 策略创建后将自动在后台执行</p>
      </div>

      <!-- 追踪止损 -->
      <div v-show="strategyMode === 'trailing_stop'" class="strategy-content">
        <div class="form-grid">
          <div class="form-group"><label>交易对</label>
            <SymbolSelector v-model="tsForm.symbol" :symbols="spotSymbols" size="small" />
          </div>
          <div class="form-group"><label>方向</label>
            <div class="side-group">
              <button :class="['side-btn', { active: tsForm.side === 'sell' }]" @click="tsForm.side = 'sell'">卖出</button>
              <button :class="['side-btn', { active: tsForm.side === 'buy' }]" @click="tsForm.side = 'buy'">买入</button>
            </div>
          </div>
          <div class="form-group"><label>追踪距离</label>
            <div style="display:flex;gap:6px;align-items:center">
              <input v-model.number="tsForm.distance" type="number" min="0.1" step="0.1" class="input" style="flex:1" />
              <select v-model="tsForm.distanceType" class="input" style="width:80px">
                <option value="percent">%</option>
                <option value="absolute">USDT</option>
              </select>
            </div>
          </div>
          <div class="form-group"><label>数量</label><input v-model.number="tsForm.sz" type="number" min="0.001" step="0.001" class="input" /></div>
          <div class="form-group"><label>策略名称（可选）</label><input v-model="tsForm.name" placeholder="如 BTC 追踪止损" class="input" /></div>
        </div>
        <div class="preview-info">
          <div class="preview-item"><span>方向</span><b>{{ tsForm.side === 'sell' ? '卖出' : '买入' }}</b></div>
          <div class="preview-item"><span>追踪距离</span><b>{{ tsForm.distance }}{{ tsForm.distanceType === 'percent' ? '%' : ' USDT' }}</b></div>
        </div>
        <div class="form-actions">
          <button class="btn primary" :disabled="tsSubmitting" @click="createTrailingStop">{{ tsSubmitting ? '创建中...' : '创建追踪止损' }}</button>
        </div>
        <div v-if="tsResult" class="order-result">✅ 策略已创建 (ID: {{ tsResult.id }})</div>
        <div v-if="tsError" class="error">{{ tsError }}</div>
        <p class="tip">💡 追踪止损将在后台监控价格，触发时自动下单</p>
      </div>

      <!-- 冰山订单 -->
      <div v-show="strategyMode === 'iceberg'" class="strategy-content">
        <div class="form-grid">
          <div class="form-group"><label>交易对</label>
            <SymbolSelector v-model="ibForm.symbol" :symbols="spotSymbols" size="small" />
          </div>
          <div class="form-group"><label>方向</label>
            <div class="side-group">
              <button :class="['side-btn', { active: ibForm.side === 'buy' }]" @click="ibForm.side = 'buy'">买入</button>
              <button :class="['side-btn', 'sell', { active: ibForm.side === 'sell' }]" @click="ibForm.side = 'sell'">卖出</button>
            </div>
          </div>
          <div class="form-group"><label>总数量</label><input v-model.number="ibForm.totalQty" type="number" min="0.001" step="0.001" class="input" /></div>
          <div class="form-group"><label>每单可见数量</label><input v-model.number="ibForm.visibleQty" type="number" min="0.001" step="0.001" class="input" /></div>
          <div class="form-group"><label>限价 (USDT)</label><input v-model.number="ibForm.limitPrice" type="number" min="0.01" step="0.01" class="input" /></div>
          <div class="form-group"><label>策略名称（可选）</label><input v-model="ibForm.name" placeholder="如 BTC 冰山" class="input" /></div>
        </div>
        <div class="preview-info">
          <div class="preview-item"><span>拆单数</span><b>{{ Math.ceil(ibForm.totalQty / ibForm.visibleQty) }} 单</b></div>
          <div class="preview-item"><span>总金额</span><b>{{ (ibForm.totalQty * ibForm.limitPrice).toFixed(2) }} USDT</b></div>
        </div>
        <div class="form-actions">
          <button class="btn primary" :disabled="ibSubmitting" @click="createIceberg">{{ ibSubmitting ? '创建中...' : '创建冰山订单' }}</button>
        </div>
        <div v-if="ibResult" class="order-result">✅ 策略已创建 (ID: {{ ibResult.id }})</div>
        <div v-if="ibError" class="error">{{ ibError }}</div>
        <p class="tip">💡 冰山订单将总数量拆分为多个小单依次发送</p>
      </div>

      <!-- TWAP -->
      <div v-show="strategyMode === 'twap'" class="strategy-content">
        <div class="form-grid">
          <div class="form-group"><label>交易对</label>
            <SymbolSelector v-model="twapForm.symbol" :symbols="spotSymbols" size="small" />
          </div>
          <div class="form-group"><label>方向</label>
            <div class="side-group">
              <button :class="['side-btn', { active: twapForm.side === 'buy' }]" @click="twapForm.side = 'buy'">买入</button>
              <button :class="['side-btn', 'sell', { active: twapForm.side === 'sell' }]" @click="twapForm.side = 'sell'">卖出</button>
            </div>
          </div>
          <div class="form-group"><label>总数量</label><input v-model.number="twapForm.totalQty" type="number" min="0.001" step="0.001" class="input" /></div>
          <div class="form-group"><label>执行时长 (分钟)</label><input v-model.number="twapForm.duration" type="number" min="1" step="1" class="input" /></div>
          <div class="form-group"><label>拆单次数</label><input v-model.number="twapForm.slices" type="number" min="2" max="100" class="input" /></div>
          <div class="form-group"><label>限价 (可选)</label><input v-model.number="twapForm.limitPrice" type="number" min="0.01" step="0.01" class="input" placeholder="0=市价" /></div>
          <div class="form-group"><label>策略名称（可选）</label><input v-model="twapForm.name" placeholder="如 BTC TWAP" class="input" /></div>
        </div>
        <div class="preview-info">
          <div class="preview-item"><span>每单数量</span><b>{{ (twapForm.totalQty / twapForm.slices).toFixed(4) }}</b></div>
          <div class="preview-item"><span>间隔时间</span><b>{{ (twapForm.duration / twapForm.slices).toFixed(1) }} 分钟</b></div>
        </div>
        <div class="form-actions">
          <button class="btn primary" :disabled="twapSubmitting" @click="createTWAP">{{ twapSubmitting ? '创建中...' : '创建 TWAP' }}</button>
        </div>
        <div v-if="twapResult" class="order-result">✅ 策略已创建 (ID: {{ twapResult.id }})</div>
        <div v-if="twapError" class="error">{{ twapError }}</div>
        <p class="tip">💡 TWAP 将大单按时间均匀拆分为小单执行</p>
      </div>
    </div>

    <!-- ===== 确认下单 Modal ===== -->
    <Teleport to="body">
      <div v-if="showConfirm" class="confirm-overlay" @click.self="showConfirm = false">
        <div class="confirm-modal">
          <h3>确认下单</h3>
          <div class="confirm-detail">
            <div class="confirm-row"><span class="label">交易对</span><span>{{ confirmSymbol }}</span></div>
            <div class="confirm-row"><span class="label">方向</span><span :class="confirmSideClass">{{ confirmSideText }}</span></div>
            <div class="confirm-row"><span class="label">价格</span><span>{{ confirmPx }}</span></div>
            <div class="confirm-row"><span class="label">数量</span><span>{{ confirmSz }} {{ confirmUnit }}</span></div>
            <div class="confirm-row"><span class="label">类型</span><span>{{ confirmOrdType }}</span></div>
            <div class="confirm-row" v-if="showLever"><span class="label">杠杆</span><span>{{ confirmLever }}x</span></div>
          </div>
          <div v-if="orderError" class="error">{{ orderError }}</div>
          <div v-if="orderResult" class="order-result">
            ✅ 已提交，订单 ID: {{ orderResult.ordId }}
          </div>
          <div class="confirm-actions">
            <button class="btn primary" :disabled="orderSubmitting" @click="submitOrder">
              {{ orderSubmitting ? '提交中...' : '确认' }}
            </button>
            <button class="btn secondary" @click="showConfirm = false">取消</button>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import SymbolSelector from '../chart/SymbolSelector.vue'

const props = defineProps<{ symbol?: string; currency?: string }>()
const emit = defineEmits<{ (e: 'open-account'): void }>()

const {
  positions,
  session,
  balance,
  error: authError,
  isLoggedIn,
  fetchPositions,
  fetchBalance,
} = useAuth()

const tradePerm = computed(() => session.value?.trade_permission ?? false)
const spotPrice = ref(0)

const spotSymbols = ref<string[]>([])
const contractSymbols = ref<string[]>([])

async function fetchSymbols(): Promise<void> {
  try {
    const [spotResp, swapResp] = await Promise.all([
      fetch('/api/account/symbols/?type=SPOT'),
      fetch('/api/account/symbols/?type=SWAP'),
    ])
    const spotData = await spotResp.json()
    const swapData = await swapResp.json()
    if (spotData.code === 0) spotSymbols.value = spotData.data
    if (swapData.code === 0) contractSymbols.value = swapData.data
  } catch { /* ignore */ }
}

function onSymbolChange(_type: 'spot' | 'contract'): void {
  fetchTicker()
}

// 从 ticker API 获取当前价格
async function fetchTicker(): Promise<void> {
  const sym = activeTab.value === 'contract' ? contractForm.symbol : spotForm.symbol
  try {
    const resp = await fetch(`/api/ticker/?symbol=${sym}&source=okx&mode=spot`)
    const result = await resp.json()
    if (result.code === 0 && result.data) {
      spotPrice.value = result.data.last || 0
      if (spotForm.ordType === 'limit') spotForm.px = spotPrice.value
    }
  } catch { /* ignore */ }
}

const strategyMode = ref<'dca' | 'grid' | 'trailing_stop' | 'iceberg' | 'twap'>('dca')
const activeTab = ref<'spot' | 'contract' | 'option' | 'position' | 'strategy'>('position')

// ---- DCA 表单 ----
const dcaForm = reactive({
  symbol: props.symbol || 'BTCUSDT',
  amount: 10,
  intervalHours: 24,
  maxExecutions: 0,
  name: '',
})
const dcaSubmitting = ref(false)
const dcaResult = ref<any>(null)
const dcaError = ref('')

const dcaSummary = computed(() => {
  const times = dcaForm.maxExecutions > 0 ? `最多 ${dcaForm.maxExecutions} 次` : '不限次数'
  const interval = { 1: '每小时', 4: '每4小时', 8: '每8小时', 24: '每天', 168: '每周' }
  return `${interval[dcaForm.intervalHours as keyof typeof interval] || '每天'} · ${times}`
})

async function createDCA(): Promise<void> {
  dcaSubmitting.value = true
  dcaError.value = ''
  dcaResult.value = null
  try {
    const resp = await fetch('/api/strategies/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'dca',
        symbol: dcaForm.symbol,
        amount: dcaForm.amount,
        interval_hours: dcaForm.intervalHours,
        max_executions: dcaForm.maxExecutions,
        name: dcaForm.name || `${dcaForm.symbol} 定投`,
      }),
    })
    const result = await resp.json()
    if (result.code === 0) {
      dcaResult.value = result.data
    } else {
      dcaError.value = result.error || '创建失败'
    }
  } catch (e: any) {
    dcaError.value = e.message || '网络错误'
  } finally {
    dcaSubmitting.value = false
  }
}

// ---- 追踪止损表单 ----
const tsForm = reactive({
  symbol: props.symbol || 'BTCUSDT',
  side: 'sell',
  distance: 5,
  distanceType: 'percent',
  sz: 0.01,
  name: '',
})
const tsSubmitting = ref(false)
const tsResult = ref<any>(null)
const tsError = ref('')

async function createTrailingStop(): Promise<void> {
  tsSubmitting.value = true
  tsError.value = ''
  tsResult.value = null
  try {
    const resp = await fetch('/api/strategies/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'trailing_stop',
        symbol: tsForm.symbol,
        name: tsForm.name || `${tsForm.symbol} 追踪止损`,
        params: {
          side: tsForm.side,
          distance: tsForm.distance,
          distance_type: tsForm.distanceType,
          sz: tsForm.sz,
        },
      }),
    })
    const result = await resp.json()
    if (result.code === 0) {
      tsResult.value = result.data
    } else {
      tsError.value = result.error || '创建失败'
    }
  } catch (e: any) {
    tsError.value = e.message || '网络错误'
  } finally {
    tsSubmitting.value = false
  }
}

// ---- 冰山订单表单 ----
const ibForm = reactive({
  symbol: props.symbol || 'BTCUSDT',
  side: 'buy',
  totalQty: 1,
  visibleQty: 0.1,
  limitPrice: 0,
  name: '',
})
const ibSubmitting = ref(false)
const ibResult = ref<any>(null)
const ibError = ref('')

async function createIceberg(): Promise<void> {
  ibSubmitting.value = true
  ibError.value = ''
  ibResult.value = null
  try {
    const resp = await fetch('/api/strategies/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'iceberg',
        symbol: ibForm.symbol,
        name: ibForm.name || `${ibForm.symbol} 冰山`,
        params: {
          side: ibForm.side,
          total_qty: ibForm.totalQty,
          visible_qty: ibForm.visibleQty,
          limit_price: ibForm.limitPrice,
        },
      }),
    })
    const result = await resp.json()
    if (result.code === 0) {
      ibResult.value = result.data
    } else {
      ibError.value = result.error || '创建失败'
    }
  } catch (e: any) {
    ibError.value = e.message || '网络错误'
  } finally {
    ibSubmitting.value = false
  }
}

// ---- TWAP 表单 ----
const twapForm = reactive({
  symbol: props.symbol || 'BTCUSDT',
  side: 'buy',
  totalQty: 1,
  duration: 60,
  slices: 6,
  limitPrice: 0,
  name: '',
})
const twapSubmitting = ref(false)
const twapResult = ref<any>(null)
const twapError = ref('')

async function createTWAP(): Promise<void> {
  twapSubmitting.value = true
  twapError.value = ''
  twapResult.value = null
  try {
    const resp = await fetch('/api/strategies/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'twap',
        symbol: twapForm.symbol,
        name: twapForm.name || `${twapForm.symbol} TWAP`,
        params: {
          side: twapForm.side,
          total_qty: twapForm.totalQty,
          duration_minutes: twapForm.duration,
          slices: twapForm.slices,
          limit_price: twapForm.limitPrice || null,
        },
      }),
    })
    const result = await resp.json()
    if (result.code === 0) {
      twapResult.value = result.data
    } else {
      twapError.value = result.error || '创建失败'
    }
  } catch (e: any) {
    twapError.value = e.message || '网络错误'
  } finally {
    twapSubmitting.value = false
  }
}

const posLoading = ref(false)
const posError = ref('')
const filterSymbol = ref('')
const expandedSymbol = ref<string | null>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

// ---- 现货表单 ----
const spotForm = reactive({
  symbol: props.symbol || 'BTCUSDT',
  side: 'buy',
  ordType: 'limit',
  px: spotPrice.value || 0,
  sz: 0.01,
  szMode: 'base',
})

// ---- 合约表单 ----
const contractForm = reactive({
  symbol: props.symbol || 'BTCUSDT',
  side: 'long',
  tdMode: 'cross',
  lever: 5,
  sz: 0.01,
  szMode: 'coin',
})

// ---- 期权表单 ----
const optionUlyList = ['BTC-USD', 'ETH-USD', 'SOL-USD']
const allOptionInstruments = ref<any[]>([])
const optionChainRows = ref<{ strike: number; call: any; put: any }[]>([])
const selectedOption = ref<any>(null)
const optionTicker = ref<any>(null)
const selectedStrike = ref<number | null>(null)

const optionForm = reactive({
  uly: 'BTC-USD',
  expTime: 0,
  optType: 'C',
  side: 'buy',
  ordType: 'limit',
  px: 0,
  sz: 1,
})

const sortedExpiries = computed(() => {
  const map = new Map<number, string>()
  for (const inst of allOptionInstruments.value) {
    const t = inst.exp_time
    const d = new Date(t * 1000)
    const label = d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    if (!map.has(t) || label) map.set(t, label)
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a - b)
    .slice(0, 10)
    .map(([value, label]) => ({ value, label }))
})

async function fetchOptionInstruments(): Promise<void> {
  try {
    const resp = await fetch(`/api/options/instruments/?uly=${optionForm.uly}`)
    const result = await resp.json()
    if (result.code === 0) {
      allOptionInstruments.value = result.data
      if (sortedExpiries.value.length) {
        optionForm.expTime = sortedExpiries.value[0].value
      }
      buildOptionChain()
    }
  } catch { /* ignore */ }
}

function buildOptionChain(): void {
  const exp = optionForm.expTime
  const filtered = allOptionInstruments.value.filter((i: any) => i.exp_time === exp)
  const strikes = new Set(filtered.map((i: any) => i.strike))
  const rows: { strike: number; call: any; put: any }[] = []
  for (const s of strikes) {
    const call = filtered.find((i: any) => i.strike === s && i.opt_type === 'C')
    const put = filtered.find((i: any) => i.strike === s && i.opt_type === 'P')
    rows.push({ strike: s, call, put })
  }
  rows.sort((a, b) => a.strike - b.strike)
  optionChainRows.value = rows
}

function onOptionChange(): void {
  buildOptionChain()
  selectedOption.value = null
  optionTicker.value = null
  selectedStrike.value = null
}

async function selectOption(inst: any, optType: string): Promise<void> {
  selectedOption.value = inst
  optionForm.optType = optType
  selectedStrike.value = inst.strike
  optionForm.px = 0
  // 同步获取该期权行权价的 bid/ask 并刷新链条显示
  try {
    const resp = await fetch(`/api/options/ticker/?instId=${inst.inst_id}`)
    const result = await resp.json()
    if (result.code === 0) {
      optionTicker.value = result.data
      // 将 ticker 中的 bid/ask 写回 optionChainRows 对应行
      const tk = result.data
      for (const row of optionChainRows.value) {
        if (row.call && row.call.strike === inst.strike) row.call.bid = tk.bid
        if (row.call && row.call.strike === inst.strike) row.call.ask = tk.ask
        if (row.put && row.put.strike === inst.strike) row.put.bid = tk.bid
        if (row.put && row.put.strike === inst.strike) row.put.ask = tk.ask
      }
      if (tk.ask > 0) optionForm.px = tk.ask
      else if (tk.last > 0) optionForm.px = tk.last
    }
  } catch { /* ignore */ }
}

// 单位
const spotUnit = computed(() => spotForm.szMode === 'base' ? spotForm.symbol.replace(/USDT|USD|USDC/, '') : 'USDT')
const contractUnit = computed(() => contractForm.szMode === 'coin' ? contractForm.symbol.replace(/USDT|USD|USDC/, '') : '张')

// 可用余额
const availSpot = computed(() => {
  if (!balance.value?.details) return '-'
  const usdt = balance.value.details.find((d: any) => d.ccy === 'USDT')
  return usdt ? `${parseFloat(usdt.availBal).toFixed(2)} USDT` : '-'
})

// 预计保证金
const estMargin = computed(() => {
  if (!spotPrice.value || !contractForm.sz) return '-'
  const val = (spotPrice.value * contractForm.sz) / contractForm.lever
  return `${val.toFixed(4)} USDT`
})

// ---- 确认 Modal ----
const showConfirm = ref(false)
const orderSubmitting = ref(false)
const orderError = ref('')
const orderResult = ref<any>(null)

const isContract = computed(() => activeTab.value === 'contract')
const isOption = computed(() => activeTab.value === 'option')
const f = computed(() => {
  return isOption.value ? (optionForm as unknown as typeof spotForm) : (isContract.value ? contractForm : spotForm)
})
const confirmSymbol = computed(() => {
  if (isOption.value && selectedOption.value) return selectedOption.value.inst_id
  return f.value.symbol
})
const confirmSideText = computed(() => {
  if (isOption.value) return optionForm.side === 'buy' ? '买入看涨' : (optionForm.optType === 'C' ? '卖出看涨' : '卖出看跌')
  if (isContract.value) return f.value.side === 'long' ? '做多' : '做空'
  return f.value.side === 'buy' ? '买入' : '卖出'
})
const confirmSideClass = computed(() => {
  const side = isOption.value ? optionForm.side : f.value.side
  const classes: Record<string, string> = {
    buy: 'text-green', long: 'text-green',
    sell: 'text-red', short: 'text-red',
  }
  return classes[side] || ''
})
const confirmPx = computed(() => {
  if (isOption.value) return optionForm.ordType === 'market' ? '市价' : (optionForm.px || '-')
  return isContract.value ? (spotPrice.value || '-') : (spotForm.ordType === 'market' ? '市价' : spotForm.px)
})
const confirmSz = computed(() => f.value.sz)
const confirmUnit = computed(() => {
  if (isOption.value) return '张'
  return isContract.value ? contractUnit.value : spotUnit.value
})
const confirmOrdType = computed(() => {
  if (isOption.value) return optionForm.ordType === 'limit' ? '限价单' : '市价单'
  if (!isContract.value) return spotForm.ordType === 'limit' ? '限价单' : '市价单'
  return '限价单'
})
const showLever = computed(() => isContract.value)
const confirmLever = computed(() => contractForm.lever)

async function submitOrder(): Promise<void> {
  if (orderSubmitting.value) return
  orderSubmitting.value = true
  orderError.value = ''
  orderResult.value = null
  try {
    const body: any = {}
    if (isOption.value) {
      body.instId = selectedOption.value?.inst_id
      body.side = optionForm.side
      body.ordType = optionForm.ordType
      body.sz = String(optionForm.sz)
      body.tdMode = 'isolated'
      if (body.ordType === 'limit') body.px = String(optionForm.px)
    } else {
      body.instId = f.value.symbol
      body.side = isContract.value ? (f.value.side === 'long' ? 'buy' : 'sell') : f.value.side
      body.ordType = isContract.value ? 'limit' : spotForm.ordType
      body.sz = String(f.value.sz)
      body.tdMode = isContract.value ? contractForm.tdMode : 'cash'
      if (body.ordType === 'limit') {
        body.px = String(isContract.value ? spotPrice.value : spotForm.px)
      }
      if (isContract.value) {
        body.posSide = f.value.side
        body.lever = String(contractForm.lever)
      }
    }
    const resp = await fetch('/api/account/place-order/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const result = await resp.json()
    if (result.code === 0) {
      orderResult.value = result.data
    } else {
      orderError.value = result.error || '下单失败'
    }
  } catch (e: any) {
    orderError.value = e.message || '网络错误'
  } finally {
    orderSubmitting.value = false
  }
}

// ---- 仓位 ----
const filteredPositions = computed(() => {
  if (!filterSymbol.value) return positions.value
  const q = filterSymbol.value.toUpperCase()
  return positions.value.filter((p: any) => p.symbol.includes(q))
})

const totalNotional = computed(() => {
  return filteredPositions.value
    .reduce((s: number, p: any) => s + (parseFloat(p.notionalValue) || 0), 0)
    .toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const totalUnrealizedPnl = computed(() => {
  return filteredPositions.value.reduce((s: number, p: any) => s + (parseFloat(p.unrealizedPnl) || 0), 0)
})

const longCount = computed(() => filteredPositions.value.filter((p: any) => p.side?.toLowerCase() === 'long').length)
const shortCount = computed(() => filteredPositions.value.filter((p: any) => p.side?.toLowerCase() === 'short').length)
const spotCount = computed(() => filteredPositions.value.filter((p: any) => p.side?.toLowerCase() === 'spot').length)

function toggleExpand(key: string): void {
  expandedSymbol.value = expandedSymbol.value === key ? null : key
}

const loadPositions = async (): Promise<void> => {
  if (!isLoggedIn.value) return
  posLoading.value = true
  posError.value = ''
  await fetchPositions()
  posLoading.value = false
  if (authError.value) posError.value = authError.value
}

watch(isLoggedIn, (loggedIn) => {
  if (loggedIn) {
    posError.value = ''
    loadPositions()
    fetchBalance()
  } else {
    positions.value = []
    posError.value = ''
    filterSymbol.value = ''
    expandedSymbol.value = null
  }
})

const formatNumber = (num: number | string): string => {
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (!n || isNaN(n)) return '-'
  if (Math.abs(n) >= 1000000) return (n / 1000000).toFixed(2) + 'M'
  if (Math.abs(n) >= 1000) return (n / 1000).toFixed(2) + 'K'
  return n.toFixed(Math.abs(n) < 1 ? 6 : 2)
}

const formatTime = (ts: string | number): string => {
  if (!ts) return '-'
  const n = typeof ts === 'string' ? parseInt(ts) : ts
  return new Date(n).toLocaleString('zh-CN', { hour12: false })
}

// ---- 网格 ----
const gridForm = reactive({
  symbol: 'BTCUSDT',
  grids: 20,
  lower: 50000,
  upper: 60000,
  invest: 1000,
  mode: 'arithmetic' as 'arithmetic' | 'geometric',
})

const gridFund = computed(() => gridForm.grids <= 0 ? 0 : gridForm.invest / gridForm.grids)
const stepPreview = computed(() => {
  const g = Math.max(2, gridForm.grids)
  if (gridForm.mode === 'arithmetic') {
    const step = (gridForm.upper - gridForm.lower) / (g - 1)
    return step > 0 ? step.toFixed(2) : '-'
  }
  if (gridForm.lower <= 0 || gridForm.upper <= 0) return '-'
  const ratio = Math.pow(gridForm.upper / gridForm.lower, 1 / (g - 1))
  return ratio > 0 ? ratio.toFixed(4) + 'x' : '-'
})

const createGrid = () => console.log('[GridTrading] create', { ...gridForm })

watch(activeTab, (tab) => {
  if (tab === 'spot' || tab === 'contract') fetchTicker()
  if (tab === 'option') fetchOptionInstruments()
})

// 交易对变更时更新行情价格
watch(() => spotForm.symbol, () => { if (activeTab.value === 'spot') fetchTicker() })
watch(() => contractForm.symbol, () => { if (activeTab.value === 'contract') fetchTicker() })

watch(() => props.symbol, (sym) => {
  if (sym) {
    spotForm.symbol = sym
    contractForm.symbol = sym
  }
})

onMounted(() => {
  fetchSymbols()
  fetchOptionInstruments()
  if (isLoggedIn.value) {
    loadPositions()
    fetchBalance()
  }
})

onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })
</script>

<style scoped>
.trading-tools-panel { background: #1e222d; border: 1px solid #2a2e39; border-radius: 8px; overflow: hidden; }
.tools-tabs { display: flex; background: #12151c; border-bottom: 1px solid #2a2e39; padding: 0 12px; gap: 4px; overflow-x: auto; }
.tab-btn { padding: 12px 16px; background: none; border: none; border-bottom: 2px solid transparent; color: #787b86; cursor: pointer; font-size: 13px; transition: all 0.2s; white-space: nowrap; }
.tab-btn:hover { color: #d1d4dc; background: rgba(255,255,255,0.03); }
.tab-btn.active { color: #2962ff; border-bottom-color: #2962ff; }
.tab-content { padding: 16px; max-height: calc(100vh - 300px); overflow-y: auto; }

.login-prompt { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 20px; gap: 12px; }
.prompt-icon { font-size: 40px; }
.prompt-text { font-size: 14px; color: #8b90a0; }
.no-perm { padding: 32px; text-align: center; color: #ff9800; font-size: 14px; }

.trade-form { display: flex; flex-direction: column; gap: 12px; max-width: 360px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row label { font-size: 12px; color: #9aa3b2; }
.input { background: #1b202b; border: 1px solid #2a2e39; color: #d1d4dc; height: 36px; border-radius: 6px; padding: 0 10px; font-size: 13px; outline: none; }
.input:focus { border-color: #2962ff; }
.input[type="number"] { -moz-appearance: textfield; }

.side-group { display: flex; gap: 6px; }
.side-btn { flex:1; height: 36px; border-radius: 6px; border: 1px solid #2a2e39; background: #202534; color: #d1d4dc; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.side-btn.active { background: rgba(76,175,80,0.2); border-color: #4caf50; color: #4caf50; }
.side-btn.sell.active { background: rgba(244,67,54,0.2); border-color: #f44336; color: #f44336; }

.type-group { display: flex; gap: 6px; }
.type-btn { flex:1; height: 32px; border-radius: 6px; border: 1px solid #2a2e39; background: #202534; color: #d1d4dc; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.type-btn.active { background: rgba(41,98,255,0.15); border-color: #2962ff; color: #2962ff; }

 qty-row { display: flex; gap: 4px; align-items: center; }
 qty-row .input { flex:1; }
.unit { font-size: 12px; color: #8b90a0; min-width: 36px; }

 qty-mode-group { display: flex; gap: 4px; }
 qty-mode-btn { padding: 2px 8px; border-radius: 4px; border: 1px solid #2a2e39; background: transparent; color: #787b86; cursor: pointer; font-size: 11px; }
 qty-mode-btn.active { border-color: #2962ff; color: #2962ff; }

.balance-row { font-size: 12px; color: #8b90a0; }
.margin-preview { font-size: 12px; color: #8b90a0; padding: 8px; background: #161a23; border-radius: 4px; }
.margin-preview b { color: #d1d4dc; }

.lever-slider { width: 100%; height: 4px; accent-color: #2962ff; }

.trade-submit { width: 100%; margin-top: 4px; }

.btn { height: 36px; padding: 0 16px; border-radius: 6px; border: 1px solid #2a2e39; cursor: pointer; font-size: 13px; transition: all 0.2s; color: #d1d4dc; background: #202534; }
.btn:hover { background: #23283a; border-color: #2f3b52; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.primary { background: #2962ff; border-color: #2962ff; color: #fff; }
.btn.primary:hover { background: #1e53e5; }
.btn.secondary { background: transparent; }

.position-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.position-section { display: flex; align-items: center; gap: 8px; }
.position-section h4 { margin: 0; font-size: 14px; color: #d1d4dc; }
.total-count { font-size: 12px; color: #787b86; background: #202534; padding: 2px 8px; border-radius: 10px; }
.toolbar-actions { display: flex; align-items: center; gap: 8px; }
.search-box { position: relative; }
.search-input { width: 140px; height: 32px; background: #1b202b; border: 1px solid #2a2e39; color: #d1d4dc; border-radius: 6px; padding: 0 10px; font-size: 12px; outline: none; }
.search-input:focus { border-color: #2962ff; }
.refresh-btn { height: 32px; padding: 0 12px; border-radius: 6px; border: 1px solid #2a2e39; background: #202534; color: #d1d4dc; cursor: pointer; font-size: 12px; white-space: nowrap; }
.refresh-btn:hover:not(:disabled) { background: #23283a; border-color: #2f3b52; }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.summary-bar { display: flex; gap: 16px; padding: 10px 12px; background: #161a23; border: 1px solid #2a2e39; border-radius: 6px; margin-bottom: 12px; flex-wrap: wrap; }
.summary-item { display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
.summary-item .label { color: #787b86; }
.summary-item .value { color: #d1d4dc; font-weight: 600; }
.long-count { color: #4caf50 !important; }
.short-count { color: #f44336 !important; }
.loading, .error, .empty { padding: 20px; text-align: center; font-size: 13px; color: #8b90a0; }
.error { color: #ff6b6b; }
.position-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; margin-bottom: 16px; }
.position-card { background: #161a23; border: 1px solid #2a2e39; border-radius: 8px; padding: 12px; cursor: pointer; transition: border-color 0.2s; }
.position-card:hover { border-color: #3a3e49; }
.position-card.expanded { border-color: #2962ff; }
.pos-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.pos-title { display: flex; align-items: center; gap: 8px; }
.pos-title h5 { margin: 0; font-size: 14px; color: #e0e2e8; font-weight: 600; }
.pos-side { font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.pos-side.long { background: rgba(76,175,80,0.15); color: #4caf50; }
.pos-side.short { background: rgba(244,67,54,0.15); color: #f44336; }
.pos-side.spot { background: rgba(33,150,243,0.15); color: #2196f3; }
.spot-count { color: #2196f3 !important; }
.pos-pnl { text-align: right; display: flex; flex-direction: column; gap: 1px; font-size: 13px; font-weight: 600; }
.pnl-pct { font-size: 11px; font-weight: 400; }
.profit { color: #4caf50; }
.loss { color: #f44336; }
.pos-row { display: flex; gap: 16px; flex-wrap: wrap; }
.pos-metric { display: flex; flex-direction: column; gap: 2px; font-size: 12px; }
.pos-metric .label { color: #787b86; font-size: 11px; }
.pos-metric .value { color: #d1d4dc; font-weight: 500; }
.pos-details { margin-top: 10px; padding-top: 10px; border-top: 1px solid #2a2e39; display: flex; flex-direction: column; gap: 6px; }
.detail-row { display: flex; gap: 20px; font-size: 12px; }
.detail-item { display: flex; flex-direction: column; gap: 2px; min-width: 100px; }
.detail-item .label { color: #787b86; font-size: 11px; }
.detail-item .value { color: #d1d4dc; font-weight: 500; }
.detail-item .value.frozen { color: #ff9800; }
.pos-expand-hint { margin-top: 8px; font-size: 11px; color: #2962ff; text-align: center; }

.form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 12px; }
.form-group { display: grid; gap: 6px; }
.form-group label { font-size: 12px; color: #9aa3b2; }
.form-group input, .form-group select { background: #1b202b; border: 1px solid #2a2e39; color: #d1d4dc; height: 36px; border-radius: 6px; padding: 0 10px; font-size: 13px; outline: none; }
.form-group input:focus, .form-group select:focus { border-color: #2962ff; }
.preview-info { background: #161a23; border: 1px dashed #2a2e39; border-radius: 6px; padding: 10px; margin-bottom: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.preview-item { display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
.preview-item span { color: #8b90a0; }
.preview-item b { color: #2962ff; font-weight: 600; }
.form-actions { display: flex; gap: 8px; }
.tip { margin-top: 10px; font-size: 12px; color: #7f8694; }

/* Confirm Modal */
.confirm-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 2000; }
.confirm-modal { background: #1e222d; border: 1px solid #2a2e39; border-radius: 12px; width: 380px; padding: 24px; }
.confirm-modal h3 { margin: 0 0 16px; font-size: 16px; color: #d1d4dc; }
.confirm-detail { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.confirm-row { display: flex; justify-content: space-between; font-size: 13px; }
.confirm-row .label { color: #8b90a0; }
.text-green { color: #4caf50; }
.text-red { color: #f44336; }
.order-result { background: rgba(76,175,80,0.1); color: #4caf50; padding: 8px; border-radius: 6px; font-size: 13px; margin-bottom: 12px; }
.confirm-actions { display: flex; gap: 8px; justify-content: flex-end; }

/* 期权链 */
.option-chain { border: 1px solid #2a2e39; border-radius: 6px; overflow: hidden; font-size: 12px; margin-bottom: 8px; }
.chain-header { display: flex; background: #12151c; padding: 6px 8px; font-weight: 600; color: #787b86; font-size: 11px; }
.chain-row { display: flex; border-top: 1px solid #2a2e39; transition: background 0.15s; }
.chain-row:hover { background: rgba(255,255,255,0.03); }
.chain-row.selected { background: rgba(41,98,255,0.08); }
.col-strike { width: 70px; min-width: 70px; text-align: center; padding: 4px 2px; color: #d1d4dc; display: flex; align-items: center; justify-content: center; font-size: 12px; }
.col-call, .col-put { flex: 1; padding: 2px; min-width: 0; }
.col-call.active { background: rgba(76,175,80,0.1); }
.col-put.active { background: rgba(244,67,54,0.1); }
.opt-btn { width: 100%; display: flex; justify-content: space-between; gap: 4px; padding: 4px 6px; border: none; background: none; color: #d1d4dc; cursor: pointer; border-radius: 4px; font-size: 11px; transition: all 0.15s; white-space: nowrap; }
.opt-btn:hover { background: rgba(41,98,255,0.15); }
.opt-bid { color: #4caf50; }
.opt-ask { color: #f44336; }
.no-opt { display: block; padding: 4px 6px; color: #3a3d45; text-align: center; font-size: 11px; }
.selected-info { padding: 8px; background: #12151c; border-radius: 4px; font-size: 12px; color: #8b90a0; margin-bottom: 8px; }
.ticker-info { margin-left: 8px; color: #2962ff; }

/* 策略交易子标签 */
.strategy-sub-tabs { display: flex; gap: 4px; margin-bottom: 12px; padding: 4px; background: #12151c; border-radius: 6px; }
.sub-tab-btn { flex: 1; padding: 8px 12px; border: none; border-radius: 4px; background: transparent; color: #787b86; cursor: pointer; font-size: 12px; transition: all 0.2s; white-space: nowrap; }
.sub-tab-btn:hover { color: #d1d4dc; background: rgba(255,255,255,0.03); }
.sub-tab-btn.active { color: #2962ff; background: rgba(41,98,255,0.15); }
.sub-tab-btn.disabled { opacity: 0.4; cursor: not-allowed; }
.strategy-content { }
</style>
