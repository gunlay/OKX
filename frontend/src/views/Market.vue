<template>
  <div class="market-container">
    <div class="header">
      <h2>行情中心</h2>
      <button class="refresh-btn" @click="refreshData" :disabled="loading">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>

    <div v-if="loading && marketData.length === 0" class="loading">
      加载中...
    </div>

    <div v-if="error" class="error">
      {{ error }}
    </div>

    <div v-if="marketData.length > 0" class="market-list">
      <div 
        v-for="item in marketData" 
        :key="item.symbol" 
        class="market-item"
      >
        <div class="symbol-info">
          <div class="symbol">{{ item.symbol }}</div>
          <div class="pair">{{ item.instId }}</div>
        </div>
        
        <div class="price-section">
          <div class="current-price">
            <span class="label">当前价</span>
            <span class="value">${{ formatPrice(item.price) }}</span>
          </div>
        </div>
        
        <div class="stats-section">
          <div class="stat-row">
            <div class="stat-item">
              <span class="label">24h最高</span>
              <span class="value">${{ formatPrice(item.high24h) }}</span>
            </div>
            <div class="stat-item">
              <span class="label">24h最低</span>
              <span class="value">${{ formatPrice(item.low24h) }}</span>
            </div>
          </div>
          
          <div class="stat-row">
            <div class="stat-item">
              <span class="label">24h涨跌</span>
              <span 
                class="value change" 
                :class="{ 
                  'positive': item.change24h > 0, 
                  'negative': item.change24h < 0,
                  'neutral': item.change24h === 0
                }"
              >
                {{ item.changePercent24h }}
              </span>
            </div>
            <div class="stat-item">
              <span class="label">当日涨跌</span>
              <span 
                class="value change" 
                :class="{ 
                  'positive': item.changeDaily > 0, 
                  'negative': item.changeDaily < 0,
                  'neutral': item.changeDaily === 0
                }"
              >
                {{ item.changePercentDaily }}
              </span>
            </div>
          </div>
          
          <div class="stat-row">
            <div class="stat-item">
              <span class="label">距24h最高</span>
              <span 
                class="value change" 
                :class="{ 
                  'positive': item.changeFromHigh > 0, 
                  'negative': item.changeFromHigh < 0,
                  'neutral': item.changeFromHigh === 0
                }"
              >
                {{ item.changeFromHighPercent }}
              </span>
            </div>
            <div class="stat-item">
              <span class="label">距24h最低</span>
              <span 
                class="value change" 
                :class="{ 
                  'positive': item.changeFromLow > 0, 
                  'negative': item.changeFromLow < 0,
                  'neutral': item.changeFromLow === 0
                }"
              >
                {{ item.changeFromLowPercent }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!loading && marketData.length === 0 && !error" class="empty">
      <p>暂无行情数据</p>
      <p class="hint">请先在配置中心选择交易币种</p>
    </div>
  </div>
</template>

<script>
import api, { marketApi } from '../api.js'

export default {
  name: 'Market',
  data() {
    return {
      marketData: [],
      loading: false,
      error: null
    }
  },
  mounted() {
    this.loadMarketData()
  },
  methods: {
    async loadMarketData() {
      this.loading = true
      this.error = null
      
      try {
        const response = await marketApi.getTickers()
        
        if (response.data.code === '0') {
          this.marketData = response.data.data
        } else {
          this.error = response.data.msg || '获取行情数据失败'
        }
      } catch (error) {
        console.error('获取行情数据失败:', error)
        console.error('错误详情:', error.response?.data || error.message)
        if (error.response?.data?.msg) {
          this.error = error.response.data.msg
        } else if (error.response?.status) {
          this.error = `请求失败 (${error.response.status}): ${error.response.statusText}`
        } else {
          this.error = `网络错误: ${error.message}`
        }
      } finally {
        this.loading = false
      }
    },
    
    async refreshData() {
      await this.loadMarketData()
    },
    
    formatPrice(price) {
      if (price >= 1) {
        return price.toFixed(2)
      } else if (price >= 0.01) {
        return price.toFixed(4)
      } else {
        return price.toFixed(6)
      }
    }
  }
}
</script>

<style scoped>
.market-container {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  color: #333;
}

.refresh-btn {
  padding: 8px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.refresh-btn:hover:not(:disabled) {
  background: #40a9ff;
}

.refresh-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.loading, .error, .empty {
  text-align: center;
  padding: 40px 20px;
  color: #666;
}

.error {
  color: #ff4d4f;
}

.empty .hint {
  font-size: 14px;
  color: #999;
  margin-top: 8px;
}

.market-list {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.market-item {
  padding: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.market-item:last-child {
  border-bottom: none;
}

.symbol-info {
  margin-bottom: 16px;
}

.symbol {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.pair {
  font-size: 12px;
  color: #999;
}

.price-section {
  margin-bottom: 16px;
}

.current-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.current-price .label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.current-price .value {
  font-size: 20px;
  font-weight: 700;
  color: #333;
}

.stats-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  background: #fafafa;
  border-radius: 6px;
}

.stat-item .label {
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
  text-align: center;
}

.stat-item .value {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  text-align: center;
}

.change.positive {
  color: #ff4d4f !important;  /* 红涨 */
}

.change.negative {
  color: #52c41a !important;  /* 绿跌 */
}

.change.neutral {
  color: #666 !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .market-container {
    padding: 15px;
  }
  
  .market-item {
    padding: 16px;
  }
  
  .symbol {
    font-size: 16px;
  }
  
  .current-price .value {
    font-size: 18px;
  }
  
  .stat-row {
    gap: 6px;
  }
  
  .stat-item {
    padding: 6px 4px;
  }
  
  .stat-item .label {
    font-size: 10px;
  }
  
  .stat-item .value {
    font-size: 12px;
  }
}
</style>