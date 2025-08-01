<template>
  <div class="transactions">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <!-- 币种和方向并排显示 -->
      <div class="filter-row">
        <select v-model="filters.symbol" class="filter-select">
          <option value="">全部币种</option>
          <option v-for="coin in availableCoins" :key="coin" :value="coin">{{ coin }}</option>
        </select>
        
        <select v-model="filters.direction" class="filter-select">
          <option value="">全部方向</option>
          <option value="buy">买入</option>
          <option value="sell">卖出</option>
        </select>
      </div>
      
      <!-- 开始日期和结束日期并排显示 -->
      <div class="filter-row">
        <div class="date-input">
          <label>开始日期</label>
          <input type="date" v-model="filters.startDate" />
        </div>
        <div class="date-input">
          <label>结束日期</label>
          <input type="date" v-model="filters.endDate" />
        </div>
      </div>
      
      <button class="search-btn" @click="fetchTransactions">
        <span>查询</span>
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 交易列表 -->
    <div v-else-if="transactions.length > 0" class="transaction-list">
      <div v-for="transaction in transactions" :key="transaction.id" class="transaction-item">
        <div class="transaction-header">
          <div class="task-info">
            <span class="task-name">{{ transaction.plan_title }}</span>
            <span class="execution-count">第{{ transaction.execution_count }}次</span>
          </div>
          <span class="transaction-direction" :class="transaction.direction">
            {{ transaction.direction === 'buy' ? '买入' : '卖出' }}
          </span>
        </div>
        
        <div class="transaction-content">
          <div class="transaction-info">
            <!-- 成交金额和币种放一排显示 -->
            <div class="info-row">
              <div class="info-item">
                <span class="label">成交金额:</span>
                <span class="value">${{ formatNumber(transaction.amount) }}</span>
              </div>
              <div class="info-item">
                <span class="label">币种:</span>
                <span class="value">{{ transaction.symbol }}</span>
              </div>
            </div>
            <!-- 成功交易显示成交价格和成交数量 -->
            <div v-if="transaction.status === 'success'" class="info-row">
              <div class="info-item">
                <span class="label">成交价格:</span>
                <span class="value">
                  {{ transaction.trade_price ? '$' + formatNumber(transaction.trade_price) : '-' }}
                </span>
              </div>
              <div class="info-item">
                <span class="label">成交数量:</span>
                <span class="value">
                  {{ formatQuantity(transaction.trade_quantity) }}
                </span>
              </div>
            </div>
            <!-- 状态和成交时间放一排显示 -->
            <div class="info-row">
              <div class="info-item">
                <span class="label">状态:</span>
                <span class="value" :class="transaction.status">
                  {{ transaction.status === 'success' ? '成功' : '失败' }}
                </span>
              </div>
              <div class="info-item">
                <span class="label">成交时间:</span>
                <span class="value">{{ formatDate(transaction.executed_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-icon">📊</div>
      <p>暂无交易记录</p>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script>
import { transactionApi, configApi } from '../api.js';

export default {
  name: 'Transactions',
  data() {
    return {
      filters: {
        symbol: '',
        direction: '',
        startDate: '',
        endDate: ''
      },
      transactions: [],
      availableCoins: [],
      loading: false,
      error: ''
    }
  },
  mounted() {
    this.loadCoins();
    this.fetchTransactions();
  },
  methods: {
    async loadCoins() {
      try {
        const response = await configApi.getCoinConfig();
        this.availableCoins = response.data;
        
        // 如果没有配置币种，添加默认币种
        if (!this.availableCoins || this.availableCoins.length === 0) {
          this.availableCoins = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT'];
        }
      } catch (error) {
        console.error('加载币种配置失败:', error);
        this.availableCoins = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT'];
      }
    },
    
    async fetchTransactions() {
      try {
        this.loading = true;
        this.error = '';
        
        const params = {
          limit: 100
        };
        
        if (this.filters.symbol) {
          params.symbol = this.filters.symbol;
        }
        
        if (this.filters.direction) {
          params.direction = this.filters.direction;
        }
        
        if (this.filters.startDate) {
          params.start_date = this.filters.startDate;
        }
        
        if (this.filters.endDate) {
          params.end_date = this.filters.endDate;
        }
        
        const response = await transactionApi.getTransactions(params);
        this.transactions = response.data;
      } catch (error) {
        console.error('获取交易记录失败:', error);
        this.error = '获取交易记录失败: ' + (error.response?.data?.detail || error.message);
      } finally {
        this.loading = false;
      }
    },
    
    formatNumber(num) {
      return parseFloat(num).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    },
    
    formatDate(timestamp) {
      const date = new Date(timestamp);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    },
    
    formatQuantity(quantity) {
      if (!quantity) return '-';
      return parseFloat(quantity).toString();
    }
  }
}
</script>

<style scoped>
.transactions {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.filter-bar {
  background: white;
  border-radius: 12px;
  padding: 15px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filter-row {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.filter-select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
}

.date-input {
  flex: 1;
}

.date-input label {
  display: block;
  margin-bottom: 5px;
  font-size: 12px;
  color: #666;
}

.date-input input {
  width: 100%;
  padding: 8px 6px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.search-btn {
  width: 100%;
  padding: 10px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.search-btn:hover {
  background: #40a9ff;
}

.transaction-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.transaction-item {
  background: white;
  border-radius: 12px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.transaction-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-name {
  font-weight: 600;
  color: #333;
  font-size: 16px;
}

.execution-count {
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 10px;
  white-space: nowrap;
}

.transaction-direction {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.transaction-direction.buy {
  background: #f6ffed;
  color: #52c41a;
}

.transaction-direction.sell {
  background: #fff2f0;
  color: #ff4d4f;
}

.transaction-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.transaction-info {
  flex: 1;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-item {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0; /* 允许收缩 */
}

.label {
  color: #666;
  font-size: 14px;
  margin-right: 6px;
  white-space: nowrap;
  flex-shrink: 0; /* 标签不收缩 */
}

.value {
  color: #333;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap; /* 不换行 */
  overflow: hidden;
  text-overflow: ellipsis; /* 超长显示省略号 */
}

.value.success {
  color: #52c41a;
}

.value.failed {
  color: #ff4d4f;
}

/* 加载状态 */
.loading-state {
  text-align: center;
  padding: 40px 0;
}

.loading-spinner {
  display: inline-block;
  width: 30px;
  height: 30px;
  border: 3px solid rgba(24, 144, 255, 0.2);
  border-radius: 50%;
  border-top-color: #1890ff;
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  margin: 0;
}

.error-message {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 12px;
  border-radius: 8px;
  margin-top: 20px;
  font-size: 14px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .transactions {
    padding: 10px;
  }
  
  .filter-bar {
    padding: 12px;
  }
  
  .filter-row {
    gap: 6px;
    margin-bottom: 12px;
  }
  
  .filter-select {
    padding: 8px 6px;
    font-size: 16px; /* 防止iOS缩放 */
  }
  
  .date-input input {
    padding: 8px 4px;
    font-size: 16px; /* 防止iOS缩放 */
  }
  
  .date-input label {
    font-size: 12px;
    margin-bottom: 3px;
  }
  
  .transaction-item {
    padding: 12px;
  }
  
  .transaction-header {
    margin-bottom: 10px;
  }
  
  .task-info {
    gap: 6px;
  }
  
  .task-name {
    font-size: 15px;
  }
  
  .execution-count {
    font-size: 11px;
    padding: 1px 4px;
  }
  
  .info-row {
    margin-bottom: 6px;
    gap: 8px;
  }
  
  .info-item {
    min-width: 0;
    max-width: 50%; /* 限制最大宽度 */
  }
  
  .label {
    font-size: 12px;
    margin-right: 4px;
  }
  
  .value {
    font-size: 12px;
    max-width: 100px; /* 限制值的最大宽度 */
  }
}
</style>