<template>
  <div class="home">
    <!-- 顶部用户信息 -->
    <div class="header">
      <div class="user-info">
        <span class="welcome">欢迎使用 OKX 定投服务</span>
        <button class="logout-btn" @click="logout">退出</button>
      </div>
    </div>

    <!-- 资产概览卡片 -->
    <div class="asset-overview">
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
          </div>
        </div>
      </div>
    </div>

    <!-- 饼状图 -->
    <div class="chart-section">
      <h3>资产分布</h3>
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
import { assetApi } from '../api.js';

export default {
  name: 'Home',
  data() {
    return {
      totalAssets: 0,
      totalInvestment: 0,
      totalProfit: 0,
      assetDistribution: [],
      loading: true,
      error: '',
      colors: ['#1890ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96', '#faad14', '#13c2c2', '#f5222d']
    }
  },
  mounted() {
    this.fetchAssetData();
  },
  computed: {
    filteredAssetDistribution() {
      // 过滤掉占比小于0.01%的资产
      return this.assetDistribution.filter(asset => asset.percentage >= 0.01);
    }
  },
  methods: {
    async fetchAssetData() {
      try {
        this.loading = true;
        this.error = '';
        
        const response = await assetApi.getOverview();
        const data = response.data;
        
        if (data.error) {
          this.error = data.error;
          return;
        }
        
        this.totalAssets = data.totalAssets;
        this.totalInvestment = data.totalInvestment;
        this.totalProfit = data.totalProfit;
        this.assetDistribution = data.assetDistribution;
      } catch (error) {
        console.error('获取资产数据失败:', error);
        this.error = '获取资产数据失败: ' + (error.response?.data?.detail || error.message);
      } finally {
        this.loading = false;
      }
    },
    
    formatNumber(num) {
      return num.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
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

.logout-btn {
  padding: 8px 16px;
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.asset-overview {
  margin-bottom: 30px;
}

.asset-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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
  
  .asset-card {
    padding: 15px;
  }
  
  .quick-actions {
    flex-direction: column;
  }
}
</style> 