import axios from 'axios';

const API_BASE_URL = 'http://13.158.74.102:8000/api';

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 15秒超时
});

// 简化的响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API请求失败:', error.config?.url, error.message);
    return Promise.reject(error);
  }
);

// DCA 计划相关 API
export const dcaApi = {
  // 获取所有 DCA 计划
  getPlans: () => api.get('/dca-plan'),
  
  // 创建新的 DCA 计划
  createPlan: (plan) => api.post('/dca-plan', plan),
  
  // 更新 DCA 计划
  updatePlan: (id, plan) => api.put(`/dca-plan/${id}`, plan),
  
  // 删除 DCA 计划
  deletePlan: (id) => api.delete(`/dca-plan/${id}`),

  // 更新计划状态
  updatePlanStatus: (id, status) => api.put(`/dca-plan/${id}/status`, { status }),
};

// 配置中心相关 API
export const configApi = {
  // 保存 API 配置
  saveApiConfig: (config) => api.post('/config/api', config),
  
  // 获取 API 配置
  getApiConfig: () => api.get('/config/api'),
  
  // 保存币种配置
  saveCoinConfig: (config) => api.post('/config/coins', config),
  
  // 获取币种配置
  getCoinConfig: () => api.get('/config/coins'),
  
  // 获取热门币种
  getPopularCoins: (limit = 100) => api.get('/config/popular-coins', { params: { limit } }),
  
  // 测试 API 连接
  testApiConnection: (config) => api.post('/config/test', config),
};

// 资产相关 API
export const assetApi = {
  // 获取资产概览
  getOverview: (forceRefresh = false) => {
    const params = forceRefresh ? { force_refresh: true } : {};
    return api.get('/assets/overview', { params });
  },
  // 获取资产历史数据
  // 获取资产历史数据
  getHistory: (days = 30, options = {}) => {
    return api.get('/assets/history', { 
      params: { days },
      timeout: options.timeout || 15000,
      signal: options.signal,
      ...options
    });
  },
};

// 账户相关 API
export const accountApi = {
  // 获取USDT余额
  getUsdtBalance: () => api.get('/account/usdt-balance'),
};

// 交易记录相关 API
export const transactionApi = {
  // 获取交易记录列表
  getTransactions: (params) => api.get('/transactions', { params }),
};

// 行情相关 API - 从本地后端获取
const localApi = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 15000,
});

export const marketApi = {
  // 获取行情数据 - 使用本地API
  getTickers: () => localApi.get('/market/tickers'),
};

export default api;
