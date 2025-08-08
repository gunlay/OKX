import axios from 'axios';

const API_BASE_URL = 'http://13.158.74.102:8000/api';

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

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
  getOverview: (forceRefresh = false) => api.get('/assets/overview', { params: forceRefresh ? { force_refresh: true } : {} }),
  // 获取资产历史数据
  getHistory: (days = 30, includeMetrics = false) => api.get('/assets/history', { params: { days, include_metrics: includeMetrics } }),
};

// 交易记录相关 API
export const transactionApi = {
  // 获取交易记录列表
  getTransactions: (params) => api.get('/transactions', { params }),
};

export default api; 