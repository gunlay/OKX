<template>
  <div class="settings">
    <h2>配置中心</h2>
    
    <!-- API Key 配置 -->
    <div class="config-section">
      <h3>OKX API 配置</h3>
      <div class="form-group">
        <label>API Key</label>
        <input 
          type="password" 
          v-model="apiConfig.apiKey" 
          placeholder="请输入 OKX API Key"
          class="form-input"
        />
      </div>
      
      <div class="form-group">
        <label>Secret Key</label>
        <input 
          type="password" 
          v-model="apiConfig.secretKey" 
          placeholder="请输入 OKX Secret Key"
          class="form-input"
        />
      </div>
      
      <div class="form-group">
        <label>Passphrase</label>
        <input 
          type="password" 
          v-model="apiConfig.passphrase" 
          placeholder="请输入 OKX Passphrase"
          class="form-input"
        />
      </div>
      
      <button class="save-btn" @click="saveApiConfig">保存 API 配置</button>
    </div>
    
    <!-- 可交易币种配置 -->
    <div class="config-section">
      <h3>可交易币种</h3>
      <p class="section-desc">选择您想要进行定投的币种，这些币种将在任务中心的新建任务中显示</p>
      
      <div class="coin-list">
        <div 
          v-for="coin in availableCoins" 
          :key="coin.symbol"
          class="coin-item"
          :class="{ selected: selectedCoins.includes(coin.symbol) }"
          @click="toggleCoin(coin.symbol)"
        >
          <div class="coin-info">
            <span class="coin-symbol">{{ coin.symbol }}</span>
            <span class="coin-name">{{ coin.name }}</span>
          </div>
          <div class="coin-status">
            <span v-if="selectedCoins.includes(coin.symbol)" class="selected-icon">✓</span>
          </div>
        </div>
      </div>
      
      <div class="action-buttons">
        <button class="btn secondary" @click="selectAll">全选</button>
        <button class="btn secondary" @click="clearAll">清空</button>
        <button class="btn primary" @click="saveCoinConfig">保存币种配置</button>
      </div>
    </div>
    
    <!-- 系统信息 -->
    <div class="config-section">
      <h3>系统信息</h3>
      <div class="info-list">
        <div class="info-item">
          <span class="label">版本:</span>
          <span class="value">v1.0.0</span>
        </div>
        <div class="info-item">
          <span class="label">服务器:</span>
          <span class="value">13.158.74.102</span>
        </div>
        <div class="info-item">
          <span class="label">状态:</span>
          <span class="value status-online">在线</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Settings',
  data() {
    return {
      apiConfig: {
        apiKey: '',
        secretKey: '',
        passphrase: ''
      },
      selectedCoins: ['BTC-USDT', 'ETH-USDT'],
      availableCoins: [
        { symbol: 'BTC-USDT', name: '比特币' },
        { symbol: 'ETH-USDT', name: '以太坊' },
        { symbol: 'BNB-USDT', name: '币安币' },
        { symbol: 'ADA-USDT', name: '卡尔达诺' },
        { symbol: 'SOL-USDT', name: '索拉纳' },
        { symbol: 'DOT-USDT', name: '波卡' },
        { symbol: 'MATIC-USDT', name: 'Polygon' },
        { symbol: 'LINK-USDT', name: 'Chainlink' },
        { symbol: 'UNI-USDT', name: 'Uniswap' },
        { symbol: 'AVAX-USDT', name: '雪崩' }
      ]
    }
  },
  mounted() {
    // 从本地存储加载配置
    this.loadConfig()
  },
  methods: {
    saveApiConfig() {
      if (!this.apiConfig.apiKey || !this.apiConfig.secretKey || !this.apiConfig.passphrase) {
        alert('请填写完整的 API 配置信息')
        return
      }
      
      // 保存到本地存储
      localStorage.setItem('okxApiConfig', JSON.stringify(this.apiConfig))
      alert('API 配置已保存')
    },
    
    saveCoinConfig() {
      if (this.selectedCoins.length === 0) {
        alert('请至少选择一个币种')
        return
      }
      
      // 保存到本地存储
      localStorage.setItem('selectedCoins', JSON.stringify(this.selectedCoins))
      alert('币种配置已保存')
    },
    
    toggleCoin(symbol) {
      const index = this.selectedCoins.indexOf(symbol)
      if (index > -1) {
        this.selectedCoins.splice(index, 1)
      } else {
        this.selectedCoins.push(symbol)
      }
    },
    
    selectAll() {
      this.selectedCoins = this.availableCoins.map(coin => coin.symbol)
    },
    
    clearAll() {
      this.selectedCoins = []
    },
    
    loadConfig() {
      // 加载 API 配置
      const savedApiConfig = localStorage.getItem('okxApiConfig')
      if (savedApiConfig) {
        this.apiConfig = JSON.parse(savedApiConfig)
      }
      
      // 加载币种配置
      const savedCoins = localStorage.getItem('selectedCoins')
      if (savedCoins) {
        this.selectedCoins = JSON.parse(savedCoins)
      }
    }
  }
}
</script>

<style scoped>
.settings {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.settings h2 {
  margin-bottom: 30px;
  color: #333;
  font-size: 24px;
}

.config-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.config-section h3 {
  margin-bottom: 15px;
  color: #333;
  font-size: 18px;
}

.section-desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.5;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #333;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
}

.save-btn {
  width: 100%;
  padding: 12px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
  margin-top: 10px;
}

.coin-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 20px;
}

.coin-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.coin-item:hover {
  border-color: #1890ff;
}

.coin-item.selected {
  border-color: #1890ff;
  background: #f0f8ff;
}

.coin-info {
  display: flex;
  flex-direction: column;
}

.coin-symbol {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.coin-name {
  color: #666;
  font-size: 12px;
}

.selected-icon {
  color: #1890ff;
  font-weight: bold;
  font-size: 16px;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn.primary {
  background: #1890ff;
  color: white;
}

.btn.secondary {
  background: #f0f0f0;
  color: #333;
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  color: #666;
  font-size: 14px;
}

.info-item .value {
  color: #333;
  font-size: 14px;
  font-weight: 500;
}

.status-online {
  color: #52c41a;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .settings {
    padding: 15px;
  }
  
  .coin-list {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style> 