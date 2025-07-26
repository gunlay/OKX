<template>
  <div class="transactions">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-row">
        <select v-model="filters.symbol" class="filter-select">
          <option value="">全部币种</option>
          <option value="BTC-USDT">BTC-USDT</option>
          <option value="ETH-USDT">ETH-USDT</option>
          <option value="BNB-USDT">BNB-USDT</option>
        </select>
        
        <select v-model="filters.direction" class="filter-select">
          <option value="">全部方向</option>
          <option value="buy">买入</option>
          <option value="sell">卖出</option>
        </select>
      </div>
      
      <div class="date-filter">
        <div class="date-input">
          <label>开始日期</label>
          <input type="date" v-model="filters.startDate" />
        </div>
        <div class="date-input">
          <label>结束日期</label>
          <input type="date" v-model="filters.endDate" />
        </div>
      </div>
    </div>

    <!-- 交易列表 -->
    <div class="transaction-list">
      <div v-for="transaction in filteredTransactions" :key="transaction.id" class="transaction-item">
        <div class="transaction-header">
          <span class="transaction-id">#{{ transaction.id }}</span>
          <span class="transaction-direction" :class="transaction.direction">
            {{ transaction.direction === 'buy' ? '买入' : '卖出' }}
          </span>
        </div>
        
        <div class="transaction-content">
          <div class="transaction-info">
            <div class="info-row">
              <span class="label">币种:</span>
              <span class="value">{{ transaction.symbol }}</span>
            </div>
            <div class="info-row">
              <span class="label">成交金额:</span>
              <span class="value">${{ transaction.amount }}</span>
            </div>
            <div class="info-row">
              <span class="label">成交数量:</span>
              <span class="value">{{ transaction.quantity }}</span>
            </div>
            <div class="info-row">
              <span class="label">成交价格:</span>
              <span class="value">${{ transaction.price }}</span>
            </div>
            <div class="info-row">
              <span class="label">成交时间:</span>
              <span class="value">{{ formatDate(transaction.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredTransactions.length === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>暂无交易记录</p>
    </div>
  </div>
</template>

<script>
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
      transactions: [
        {
          id: 1,
          symbol: 'BTC-USDT',
          direction: 'buy',
          amount: 100.00,
          quantity: 0.0032,
          price: 31250.00,
          timestamp: '2024-01-15T10:30:00Z'
        },
        {
          id: 2,
          symbol: 'ETH-USDT',
          direction: 'buy',
          amount: 50.00,
          quantity: 0.025,
          price: 2000.00,
          timestamp: '2024-01-14T14:20:00Z'
        },
        {
          id: 3,
          symbol: 'BTC-USDT',
          direction: 'sell',
          amount: 80.00,
          quantity: 0.0025,
          price: 32000.00,
          timestamp: '2024-01-13T09:15:00Z'
        }
      ]
    }
  },
  computed: {
    filteredTransactions() {
      return this.transactions.filter(transaction => {
        // 币种筛选
        if (this.filters.symbol && transaction.symbol !== this.filters.symbol) {
          return false
        }
        
        // 方向筛选
        if (this.filters.direction && transaction.direction !== this.filters.direction) {
          return false
        }
        
        // 日期筛选
        if (this.filters.startDate || this.filters.endDate) {
          const transactionDate = new Date(transaction.timestamp).toISOString().split('T')[0]
          
          if (this.filters.startDate && transactionDate < this.filters.startDate) {
            return false
          }
          
          if (this.filters.endDate && transactionDate > this.filters.endDate) {
            return false
          }
        }
        
        return true
      }).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    }
  },
  methods: {
    formatDate(timestamp) {
      const date = new Date(timestamp)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
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

.date-filter {
  display: flex;
  gap: 10px;
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
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
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

.transaction-id {
  font-weight: 600;
  color: #333;
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
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.label {
  width: 80px;
  color: #666;
  font-size: 14px;
}

.value {
  color: #333;
  font-size: 14px;
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
  font-size: 16px;
  margin: 0;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .transactions {
    padding: 15px;
  }
  
  .filter-row {
    flex-direction: column;
  }
  
  .date-filter {
    flex-direction: column;
  }
  
  .transaction-content {
    flex-direction: column;
  }
}
</style> 