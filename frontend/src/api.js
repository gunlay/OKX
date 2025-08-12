import axios from 'axios';

const API_BASE_URL = 'http://13.158.74.102:8000/api';

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 增加到30秒
});

// 请求拦截器 - 添加重试机制
api.interceptors.request.use(
  (config) => {
    // 添加请求开始时间
    config.metadata = { startTime: new Date() };
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 添加重试和错误处理
api.interceptors.response.use(
  (response) => {
    // 计算请求耗时
    const endTime = new Date();
    const duration = endTime - response.config.metadata.startTime;
    console.log(`API请求耗时: ${response.config.url} - ${duration}ms`);
    return response;
  },
  async (error) => {
    const config = error.config;
    
    // 如果没有设置重试次数，初始化为0
    if (!config.__retryCount) {
      config.__retryCount = 0;
    }
    
    // 最大重试3次
    const maxRetries = 3;
    
    // 判断是否需要重试
    const shouldRetry = (
      config.__retryCount < maxRetries &&
      (
        error.code === 'ECONNABORTED' || // 超时
        error.code === 'NETWORK_ERROR' || // 网络错误
        (error.response && [500, 502, 503, 504].includes(error.response.status)) // 服务器错误
      )
    );
    
    if (shouldRetry) {
      config.__retryCount += 1;
      
      // 指数退避延迟
      const delay = Math.pow(2, config.__retryCount) * 1000;
      console.log(`API请求失败，${delay}ms后进行第${config.__retryCount}次重试: ${config.url}`);
      
      await new Promise(resolve => setTimeout(resolve, delay));
      return api(config);
    }
    
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
  getHistory: (days = 30, includeMetrics = false) => api.get('/assets/history', { params: { days, include_metrics: includeMetrics } }),
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

export default api; 