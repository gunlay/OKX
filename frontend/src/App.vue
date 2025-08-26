<template>
  <div id="app">
    <!-- 主内容区域 -->
    <div class="main-content">
      <router-view />
    </div>
    
    <!-- 底部导航栏 -->
    <div class="bottom-nav">
      <div 
        class="nav-item" 
        :class="{ active: $route.path === '/' }"
        @click="$router.push('/')"
      >
        <i class="icon">🏠</i>
        <span>首页</span>
      </div>
      <div 
        class="nav-item" 
        :class="{ active: $route.path === '/market' }"
        @click="$router.push('/market')"
      >
        <i class="icon">📈</i>
        <span>行情</span>
      </div>
      <div 
        class="nav-item" 
        :class="{ active: $route.path === '/transactions' }"
        @click="$router.push('/transactions')"
      >
        <i class="icon">📊</i>
        <span>交易记录</span>
      </div>
      <div 
        class="nav-item" 
        :class="{ active: $route.path === '/tasks' }"
        @click="$router.push('/tasks')"
      >
        <i class="icon">📋</i>
        <span>任务中心</span>
      </div>
      <div 
        class="nav-item" 
        :class="{ active: $route.path === '/settings' }"
        @click="$router.push('/settings')"
      >
        <i class="icon">⚙️</i>
        <span>配置中心</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #f5f5f5;
  color: #333;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding-bottom: 60px; /* 为底部导航留出空间 */
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: white;
  border-top: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 1000;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  cursor: pointer;
  transition: color 0.3s;
  color: #666;
}

.nav-item.active {
  color: #1890ff;
}

.nav-item .icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.nav-item span {
  font-size: 12px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .main-content {
    padding: 10px;
  }
}
</style> 