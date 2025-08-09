<template>
  <div class="home">
    <!-- 顶部用户信息 -->
    <div class="header">
      <div class="user-info">
        <span class="welcome">欢迎使用 OKX 定投服务</span>
        <div class="header-buttons">
          <button class="refresh-btn" @click="refreshData" :disabled="refreshing">
            <span v-if="refreshing">刷新中...</span>
            <span v-else>刷新数据</span>
          </button>
          <button class="logout-btn" @click="logout">退出</button>
        </div>
      </div>
    </div>

    <!-- USDT余额显示 -->
    <div class="usdt-balance-section">
      <div class="balance-card">
        <div class="balance-header">
          <h3>OKX账户余额</h3>
          <span class="balance-refresh" @click="refreshUsdtBalance" :class="{ loading: usdtLoading }">
            🔄
          </span>
        </div>
        <div class="balance-content">
          <div class="balance-item">
            <span class="balance-label">可用USDT:</span>
            <span class="balance-value">
              <span v-if="usdtLoading" class="loading-text">加载中...</span>
              <span v-else-if="usdtBalance.error" class="error-text">{{ usdtBalance.error }}</span>
              <span v-else class="amount">${{ formatNumber(usdtBalance.balance) }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 资产概览卡片 -->
    <div class="asset-overview">
      <div class="card-header">
        <h3>定投策略资产概览</h3>
      </div>
      <div class="strategy-note">
        <i class="note-icon">ℹ️</i>
        <span>此处仅统计通过本系统执行的定投交易产生的资产和收益</span>
      </div>
      <div class="asset-card">
        <div class="asset-item">
          <div class="label">总资产</div>
          <div class="value">${{ formatNumber(totalAssets) }}</div>
        </div>
        <div class="asset-item">
          <div class="label">总投入</div>
          <div class="value">${{ formatNumber(totalInvestment) }}</div>
        </div>
        <div class="asset-item">
          <div class="label">总收益</div>
          <div class="value" :class="{ 'profit': totalProfit >= 0, 'loss': totalProfit < 0 }">
            ${{ formatNumber(totalProfit) }}
            <span class="profit-rate" :class="{ 'profit': totalProfit >= 0, 'loss': totalProfit < 0 }">
              ({{ formatProfitRate(totalProfit, totalInvestment) }})
            </span>
          </div>
        </div>
        <div class="asset-item">
          <div class="label">年化收益率</div>
          <div class="value" :class="{ 'profit': annualizedReturn >= 0, 'loss': annualizedReturn < 0 }">
            {{ formatAnnualizedReturn(annualizedReturn) }}
          </div>
        </div>
        <div class="strategy-info" v-if="strategyInfo.startDate">
          <div>策略开始: {{ formatDate(strategyInfo.startDate) }}</div>
          <div>执行次数: {{ strategyInfo.executionCount }} 次</div>
        </div>
        <div class="last-updated" v-if="lastUpdated">
          最后更新: {{ formatDateTime(lastUpdated) }}
        </div>
      </div>
    </div>

    <!-- 资产趋势图表 -->
    <AssetTrend :refresh-trigger="refreshTrigger" />
    
    <!-- 饼状图 -->
    <div class="chart-section">
      <h3>定投策略资产分布</h3>
      <div class="pie-chart">
        <div v-if="loading" class="loading-spinner"></div>
        <div v-else-if="filteredAssetDistribution.length === 0" class="no-data">
          暂无资产数据
        </div>
        <div v-else class="chart-container">
          <div class="pie-circle">
            <div 
              v-for="(asset, index) in filteredAssetDistribution" 
              :key="asset.currency"
              class="pie-segment" 
              :style="{
                '--percentage': `${asset.percentage}%`, 
                '--color': getAssetColor(index),
                '--start': `${getStartPercentage(index)}%`
              }"
            ></div>
          </div>
          <div class="legend">
            <div 
              v-for="(asset, index) in filteredAssetDistribution" 
              :key="asset.currency"
              class="legend-item"
            >
              <span class="color-dot" :style="{ background: getAssetColor(index) }"></span>
              <span>{{ asset.currency }} ({{ asset.percentage.toFixed(2) }}%)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- 快速操作 -->
    <div class="quick-actions">
      <button class="action-btn primary" @click="$router.push('/tasks')">
        新建定投任务
      </button>
      <button class="action-btn secondary" @click="$router.push('/transactions')">
        查看交易记录
      </button>
    </div>
  </div>
</template>

<script>
import { assetApi, accountApi } from '../api.js';
import AssetTrend from '../components/AssetTrend.vue';

export default {
  name: 'Home',
  components: {
    AssetTrend
  },
  data() {
    return {
      totalAssets: 0,
      totalInvestment: 0,
      totalProfit: 0,
      annualizedReturn: 0,
      assetDistribution: [],
      loading: true,
      error: '',
      lastUpdated: null,
      refreshing: false,
      refreshTrigger: 0, // 用于触发资产趋势图表刷新
      strategyInfo: {
        startDate: null,
        executionCount: 0
      },
      colors: ['#1890ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96', '#faad14', '#13c2c2', '#f5222d'],
      // USDT余额相关
      usdtBalance: {
        balance: 0,
        error: null
      },
      usdtLoading: false
    }
  },
  mounted() {
    this.fetchAssetData();
    this.fetchUsdtBalance();
  },
  computed: {
    filteredAssetDistribution() {
      // 过滤掉占比小于0.01%的资产
      return this.assetDistribution.filter(asset => asset.percentage >= 0.01);
    }
  },
  methods: {
    async fetchAssetData(forceRefresh = false) {
      try {
        this.loading = true;
        this.error = '';
        if (forceRefresh) {
          this.refreshing = true;
        }
        
        console.log('开始获取资产数据, forceRefresh:', forceRefresh);
        
        // 使用修改后的API函数，直接传递forceRefresh参数
        const response = await assetApi.getOverview(forceRefresh);
        const data = response.data;
        
        console.log('API响应数据:', data);
        
        if (data.error) {
          this.error = data.error;
          console.error('API返回错误:', data.error);
          return;
        }
        
        this.totalAssets = data.totalAssets || 0;
        this.totalInvestment = data.totalInvestment || 0;
        this.totalProfit = data.totalProfit || 0;
        this.annualizedReturn = data.annualizedReturn || 0;
        this.assetDistribution = data.assetDistribution || [];
        
        console.log('设置资产数据:', {
          totalAssets: this.totalAssets,
          totalInvestment: this.totalInvestment,
          totalProfit: this.totalProfit,
          assetDistribution: this.assetDistribution
        });
        
        // 更新策略信息
        if (data.strategyInfo) {
          this.strategyInfo = data.strategyInfo;
        }
        
        // 更新最后更新时间
        if (data.lastUpdated) {
          this.lastUpdated = new Date(data.lastUpdated);
        } else {
          this.lastUpdated = new Date();
        }
      } catch (error) {
        console.error('获取资产数据失败:', error);
        this.error = '获取资产数据失败: ' + (error.response?.data?.detail || error.message);
      } finally {
        this.loading = false;
        this.refreshing = false;
      }
    },
    
    // 手动刷新数据
    refreshData() {
      this.fetchAssetData(true);
      // 增加刷新触发器的值，触发资产趋势图表刷新
      this.refreshTrigger++;
    },
    
    // 格式化日期时间
    formatDateTime(date) {
      if (!date) return '';
      return new Date(date).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    },
    
    formatNumber(num) {
      return num.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    },
    
    formatProfitRate(profit, investment) {
      if (!investment || investment === 0) return '0.00%';
      const rate = (profit / investment) * 100;
      return `${rate >= 0 ? '+' : ''}${rate.toFixed(2)}%`;
    },
    
    formatAnnualizedReturn(rate) {
      if (!rate) return '0.00%';
      const percentage = rate * 100;
      return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`;
    },
    
    formatDate(date) {
      if (!date) return '';
      return new Date(date).toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    },
    
    getAssetColor(index) {
      return this.colors[index % this.colors.length];
    },
    
    getStartPercentage(index) {
      let start = 0;
      for (let i = 0; i < index; i++) {
        start += this.filteredAssetDistribution[i].percentage;
      }
      return start;
    },
    
    logout() {
      // 退出登录逻辑
      if (confirm('确定要退出登录吗？')) {
        // 清除用户信息
        localStorage.removeItem('user');
        // 跳转到登录页或刷新页面
        window.location.reload();
      }
    }
  }
}
</script>

<style scoped>
.home {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.header {
  margin-bottom: 20px;
}

.user-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.welcome {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.header-buttons {
  display: flex;
  gap: 10px;
  align-items: center;
}

.refresh-btn {
  padding: 8px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s;
}

.refresh-btn:hover {
  background: #40a9ff;
}

.refresh-btn:disabled {
  background: #bae7ff;
  cursor: not-allowed;
}

.logout-btn {
  padding: 8px 16px;
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.logout-btn:hover {
  background: #ff7875;
}

/* USDT余额样式 */
.usdt-balance-section {
  margin-bottom: 20px;
}

.balance-card {
  background: white;
  border-radius: 12px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.balance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.balance-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.balance-refresh {
  cursor: pointer;
  font-size: 16px;
  transition: transform 0.3s;
  user-select: none;
}

.balance-refresh:hover {
  transform: scale(1.1);
}

.balance-refresh.loading {
  animation: spin 1s linear infinite;
}

.balance-content {
  padding: 5px 0;
}

.balance-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.balance-label {
  font-size: 14px;
  color: #666;
}

.balance-value {
  font-size: 16px;
  font-weight: 600;
}

.balance-value .amount {
  color: #1890ff;
}

.balance-value .loading-text {
  color: #999;
  font-size: 14px;
}

.balance-value .error-text {
  color: #ff4d4f;
  font-size: 12px;
}

.asset-overview {
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.asset-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: relative;
}

.strategy-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #666;
  margin-top: 15px;
  padding-top: 10px;
  border-top: 1px dashed #f0f0f0;
}

.last-updated {
  font-size: 12px;
  color: #999;
  text-align: right;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #f0f0f0;
}

.asset-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.asset-item:last-child {
  border-bottom: none;
}

.label {
  font-size: 16px;
  color: #666;
}

.value {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.profit {
  color: #52c41a;
}

.loss {
  color: #ff4d4f;
}

.profit-rate {
  font-size: 14px;
  margin-left: 8px;
}

.chart-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 30px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-section h3 {
  margin-bottom: 20px;
  color: #333;
  font-size: 18px;
}

.pie-chart {
  display: flex;
  justify-content: center;
  min-height: 200px;
}

.chart-container {
  text-align: center;
  width: 100%;
}

.pie-circle {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  position: relative;
  margin: 0 auto 20px;
  background: #f5f5f5;
  overflow: hidden;
}

.pie-segment {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: conic-gradient(
    var(--color) var(--start) calc(var(--start) + var(--percentage)),
    transparent calc(var(--start) + var(--percentage)) 100%
  );
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 300px;
  margin: 0 auto;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.loading-spinner {
  display: inline-block;
  width: 30px;
  height: 30px;
  border: 3px solid rgba(24, 144, 255, 0.2);
  border-radius: 50%;
  border-top-color: #1890ff;
  animation: spin 1s ease-in-out infinite;
  margin: 50px 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.no-data {
  text-align: center;
  padding: 50px 0;
  color: #999;
  font-size: 16px;
}

.error-message {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.quick-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn.primary {
  background: #1890ff;
  color: white;
}

.action-btn.primary:hover {
  background: #40a9ff;
}

.action-btn.secondary {
  background: #f0f0f0;
  color: #333;
}

.action-btn.secondary:hover {
  background: #e0e0e0;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .home {
    padding: 15px;
  }
  
  .header-buttons {
    flex-direction: column;
    gap: 8px;
  }
  
  .refresh-btn, .logout-btn {
    padding: 6px 12px;
    font-size: 12px;
  }
  
  .balance-card {
    padding: 12px;
  }
  
  .balance-header h3 {
    font-size: 14px;
  }
  
  .balance-value {
    font-size: 14px;
  }
  
  .asset-card {
    padding: 15px;
  }
  
  .quick-actions {
    flex-direction: column;
  }
}
</style> 