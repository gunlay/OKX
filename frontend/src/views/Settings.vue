<template>
  <div class="settings-container">
    <div class="header">
      <h2>配置中心</h2>
    </div>

    <!-- API 配置部分 -->
    <div class="config-section">
      <h3>OKX API 配置</h3>
      <div class="form-group">
        <label>API Key:</label>
        <input 
          v-model="apiConfig.api_key" 
          type="password" 
          placeholder="请输入 API Key"
          :disabled="loading"
        />
      </div>
      <div class="form-group">
        <label>Secret Key:</label>
        <input 
          v-model="apiConfig.secret_key" 
          type="password" 
          placeholder="请输入 Secret Key"
          :disabled="loading"
        />
      </div>
      <div class="form-group">
        <label>Passphrase:</label>
        <input 
          v-model="apiConfig.passphrase" 
          type="password" 
          placeholder="请输入 Passphrase"
          :disabled="loading"
        />
      </div>
      <div class="button-group">
        <button @click="saveApiConfig" :disabled="loading" class="btn-primary">
          {{ loading ? '保存中...' : '保存配置' }}
        </button>
        <button @click="testConnection" :disabled="loading" class="btn-secondary">
          {{ testing ? '测试中...' : '测试连接' }}
        </button>
      </div>
      <div v-if="apiMessage" :class="['message', apiMessageType]">
        {{ apiMessage }}
      </div>
    </div>

    <!-- 币种配置部分 -->
    <div class="config-section">
      <h3>交易币种配置</h3>
      <div class="form-group">
        <label>选择交易币种:</label>
        <div class="coin-grid">
          <div 
            v-for="coin in availableCoins" 
            :key="coin"
            :class="['coin-item', { selected: selectedCoins.includes(coin) }]"
            @click="toggleCoin(coin)"
          >
            {{ coin }}
          </div>
        </div>
      </div>
      <div class="button-group">
        <button @click="saveCoinConfig" :disabled="loading" class="btn-primary">
          {{ loading ? '保存中...' : '保存币种配置' }}
        </button>
      </div>
      <div v-if="coinMessage" :class="['message', coinMessageType]">
        {{ coinMessage }}
      </div>
    </div>

    <!-- 系统信息部分 -->
    <div class="config-section">
      <h3>系统信息</h3>
      <div class="info-item">
        <span class="label">服务器地址:</span>
        <span class="value">13.158.74.102</span>
      </div>
      <div class="info-item">
        <span class="label">API 状态:</span>
        <span :class="['value', apiStatus]">{{ apiStatusText }}</span>
      </div>
      <div class="info-item">
        <span class="label">版本:</span>
        <span class="value">v1.0.0</span>
      </div>
    </div>
  </div>
</template>

<script>
import { configApi } from '../api.js';

export default {
  name: 'Settings',
  data() {
    return {
      apiConfig: {
        api_key: '',
        secret_key: '',
        passphrase: ''
      },
      selectedCoins: [],
      availableCoins: [
        'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'ADA-USDT', 'SOL-USDT',
        'DOT-USDT', 'DOGE-USDT', 'AVAX-USDT', 'MATIC-USDT', 'LINK-USDT',
        'UNI-USDT', 'LTC-USDT', 'BCH-USDT', 'XLM-USDT', 'ATOM-USDT'
      ],
      loading: false,
      testing: false,
      apiMessage: '',
      apiMessageType: '',
      coinMessage: '',
      coinMessageType: '',
      apiStatus: 'unknown',
      apiStatusText: '未知'
    };
  },
  async mounted() {
    await this.loadConfigurations();
  },
  methods: {
    async loadConfigurations() {
      try {
        this.loading = true;
        
        // 加载 API 配置
        const apiResponse = await configApi.getApiConfig();
        if (apiResponse.data) {
          this.apiConfig = {
            api_key: apiResponse.data.api_key || '',
            secret_key: apiResponse.data.secret_key || '',
            passphrase: apiResponse.data.passphrase || ''
          };
        }
        
        // 加载币种配置
        const coinResponse = await configApi.getCoinConfig();
        if (coinResponse.data) {
          this.selectedCoins = coinResponse.data;
        }
        
        this.showMessage('配置加载成功', 'success', 'api');
        
      } catch (error) {
        console.error('加载配置失败:', error);
        this.showMessage('加载配置失败: ' + (error.response?.data?.detail || error.message), 'error', 'api');
      } finally {
        this.loading = false;
      }
    },

    async saveApiConfig() {
      try {
        this.loading = true;
        this.apiMessage = '';
        
        await configApi.saveApiConfig(this.apiConfig);
        this.showMessage('API 配置保存成功', 'success', 'api');
        
      } catch (error) {
        console.error('保存 API 配置失败:', error);
        this.showMessage('保存失败: ' + (error.response?.data?.detail || error.message), 'error', 'api');
      } finally {
        this.loading = false;
      }
    },

    async saveCoinConfig() {
      try {
        this.loading = true;
        this.coinMessage = '';
        
        await configApi.saveCoinConfig({ selected_coins: this.selectedCoins });
        this.showMessage('币种配置保存成功', 'success', 'coin');
        
      } catch (error) {
        console.error('保存币种配置失败:', error);
        this.showMessage('保存失败: ' + (error.response?.data?.detail || error.message), 'error', 'coin');
      } finally {
        this.loading = false;
      }
    },

    async testConnection() {
      try {
        this.testing = true;
        this.apiMessage = '';
        
        const response = await configApi.testApiConnection(this.apiConfig);
        
        if (response.data && response.data.success) {
          this.apiStatus = 'success';
          this.apiStatusText = '连接正常';
          this.showMessage('API 连接测试成功', 'success', 'api');
        } else {
          this.apiStatus = 'error';
          this.apiStatusText = '连接失败';
          this.showMessage('API 连接测试失败: ' + (response.data?.message || '未知错误'), 'error', 'api');
        }
        
      } catch (error) {
        this.apiStatus = 'error';
        this.apiStatusText = '连接失败';
        console.error('API 连接测试失败:', error, error.response && error.response.data);
        let msg = '连接测试失败: ';
        if (error.response && error.response.data) {
          try {
            msg += JSON.stringify(error.response.data);
          } catch (e) {
            msg += error.response.data.toString();
          }
        } else {
          msg += error.message;
        }
        this.showMessage(msg, 'error', 'api');
      } finally {
        this.testing = false;
      }
    },

    toggleCoin(coin) {
      const index = this.selectedCoins.indexOf(coin);
      if (index > -1) {
        this.selectedCoins.splice(index, 1);
      } else {
        this.selectedCoins.push(coin);
      }
    },

    showMessage(message, type, target) {
      if (target === 'api') {
        this.apiMessage = message;
        this.apiMessageType = type;
        setTimeout(() => {
          this.apiMessage = '';
        }, 5000);
      } else if (target === 'coin') {
        this.coinMessage = message;
        this.coinMessageType = type;
        setTimeout(() => {
          this.coinMessage = '';
        }, 5000);
      }
    }
  }
};
</script>

<style scoped>
.settings-container {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h2 {
  color: #333;
  margin: 0;
}

.config-section {
  background: white;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.config-section h3 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 10px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #555;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.button-group {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-primary, .btn-secondary {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
}

.btn-primary {
  background: #1890ff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-primary:disabled, .btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message {
  margin-top: 10px;
  padding: 10px;
  border-radius: 6px;
  font-size: 14px;
}

.message.success {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #52c41a;
}

.message.error {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
}

.coin-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.coin-item {
  padding: 10px;
  text-align: center;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
}

.coin-item:hover {
  border-color: #1890ff;
  background: #f0f8ff;
}

.coin-item.selected {
  background: #1890ff;
  color: white;
  border-color: #1890ff;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  font-weight: 500;
  color: #555;
}

.info-item .value {
  color: #333;
}

.info-item .value.success {
  color: #52c41a;
}

.info-item .value.error {
  color: #ff4d4f;
}

.info-item .value.unknown {
  color: #faad14;
}
</style> 