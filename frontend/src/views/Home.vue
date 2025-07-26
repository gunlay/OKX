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
        <div class="chart-placeholder">
          <div class="pie-circle">
            <div class="pie-segment" style="--percentage: 60%; --color: #1890ff;"></div>
            <div class="pie-segment" style="--percentage: 40%; --color: #52c41a; --start: 60%;"></div>
          </div>
          <div class="legend">
            <div class="legend-item">
              <span class="color-dot" style="background: #1890ff;"></span>
              <span>投资资产 (60%)</span>
            </div>
            <div class="legend-item">
              <span class="color-dot" style="background: #52c41a;"></span>
              <span>未投资 USDT (40%)</span>
            </div>
          </div>
        </div>
      </div>
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
export default {
  name: 'Home',
  data() {
    return {
      totalAssets: 12500.50,
      totalInvestment: 10000.00,
      totalProfit: 2500.50
    }
  },
  methods: {
    formatNumber(num) {
      return num.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    },
    logout() {
      // 退出登录逻辑
      if (confirm('确定要退出登录吗？')) {
        // 清除用户信息
        localStorage.removeItem('user')
        // 跳转到登录页或刷新页面
        window.location.reload()
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
}

.chart-placeholder {
  text-align: center;
}

.pie-circle {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  position: relative;
  margin: 0 auto 20px;
  background: conic-gradient(
    var(--color) 0deg var(--percentage),
    transparent var(--percentage) 360deg
  );
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
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