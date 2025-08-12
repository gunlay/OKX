<template>
  <div class="asset-trend">
    <div class="card-header">
      <h3>定投策略资产趋势</h3>
      <div class="period-selector">
        <button 
          v-for="period in periods" 
          :key="period.value" 
          :class="['period-btn', { active: selectedPeriod === period.value }]"
          @click="changePeriod(period.value)"
        >
          {{ period.label }}
        </button>
      </div>
    </div>
    
    <div class="chart-container">
      <div v-if="loading" class="loading-spinner"></div>
      <div v-else-if="error" class="error-message">{{ error }}</div>
      <div v-else-if="!hasData" class="no-data">暂无历史数据</div>
      <div v-else ref="chartRef" class="chart"></div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  TooltipComponent,
  GridComponent,
  LegendComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { assetApi } from '../api.js';

// 注册必要的组件（移除不需要的DataZoomComponent和TitleComponent）
echarts.use([
  TooltipComponent,
  GridComponent,
  LegendComponent,
  LineChart,
  CanvasRenderer
]);

export default {
  name: 'AssetTrend',
  props: {
    refreshTrigger: {
      type: Number,
      default: 0
    }
  },
  setup(props) {
    const chartRef = ref(null);
    const chart = ref(null);
    const loading = ref(true);
    const error = ref('');
    const historyData = ref([]);
    const selectedPeriod = ref(30); // 默认30天
    const hasData = ref(false);
    
    const periods = [
      { label: '7天', value: 7 },
      { label: '30天', value: 30 },
      { label: '90天', value: 90 },
      { label: '全部', value: 365 }
    ];
    
    // 生成指定天数的日期数组（不包含今天，只到昨天）
    const generateDateRange = (days) => {
      const dates = [];
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(today.getDate() - 1); // 从昨天开始
      
      for (let i = days - 1; i >= 0; i--) {
        const date = new Date(yesterday);
        date.setDate(yesterday.getDate() - i);
        dates.push(date);
      }
      
      return dates;
    };
    
    // 优化的数据缓存
    const dataCache = new Map();
    const cacheTimeout = 5 * 60 * 1000; // 5分钟缓存
    let currentRequest = null; // 防止重复请求
    
    // 获取历史数据
    const fetchHistoryData = async (days) => {
      try {
        // 如果有正在进行的请求，取消它
        if (currentRequest) {
          currentRequest.cancel && currentRequest.cancel();
        }
        
        loading.value = true;
        error.value = '';
        
        // 检查缓存
        const cacheKey = `history_${days}`;
        const now = Date.now();
        
        if (dataCache.has(cacheKey)) {
          const cached = dataCache.get(cacheKey);
          if (now - cached.timestamp < cacheTimeout) {
            console.log('使用缓存数据，快速加载:', cacheKey);
            historyData.value = cached.historyData;
            hasData.value = cached.hasData;
            loading.value = false;
            
            // 异步初始化图表，不阻塞UI
            setTimeout(() => {
              initChart();
            }, 0);
            return;
          }
        }
        
        // 创建可取消的请求
        const controller = new AbortController();
        currentRequest = { cancel: () => controller.abort() };
        
        const response = await assetApi.getHistory(days, { 
          signal: controller.signal,
          timeout: 10000 // 10秒超时
        });
        const rawData = response.data || [];
        
        // 生成完整的日期范围
        const dateRange = generateDateRange(days);
        
        // 创建日期到数据的映射
        const dataMap = new Map();
        rawData.forEach(item => {
          const date = new Date(item.date);
          const dateKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
          dataMap.set(dateKey, item);
        });
        
        // 填充完整的数据数组
        const processedData = dateRange.map(date => {
          const dateKey = `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
          
          if (dataMap.has(dateKey)) {
            return dataMap.get(dateKey);
          } else {
            // 如果没有数据，使用0填充
            return {
              date: date.toISOString(),
              totalAssets: 0,
              totalInvestment: 0,
              totalProfit: 0
            };
          }
        });
        
        historyData.value = processedData;
        hasData.value = processedData.length > 0;
        
        // 缓存数据
        dataCache.set(cacheKey, {
          historyData: processedData,
          hasData: processedData.length > 0,
          timestamp: now
        });
        
        // 限制缓存大小
        if (dataCache.size > 8) {
          const firstKey = dataCache.keys().next().value;
          dataCache.delete(firstKey);
        }
        
        // 异步初始化图表，提升响应速度
        setTimeout(() => {
          initChart();
        }, 0);
      } catch (err) {
        // 如果是取消的请求，不显示错误
        if (err.name === 'AbortError' || err.code === 'ECONNABORTED') {
          console.log('请求已取消或超时');
          return;
        }
        
        console.error('获取资产历史数据失败:', err);
        let errorMessage = '数据加载失败';
        
        if (err.message?.includes('timeout')) {
          errorMessage = '加载超时，请稍后重试';
        } else if (err.response) {
          const status = err.response.status;
          if (status === 500) {
            errorMessage = '服务器异常，请稍后重试';
          } else if (status === 404) {
            errorMessage = '暂无历史数据';
          } else {
            errorMessage = err.response.data?.detail || '服务器错误';
          }
        } else if (err.request) {
          errorMessage = '网络连接失败，请检查网络';
        } else {
          errorMessage = err.message || '未知错误';
        }
        
        error.value = errorMessage;
        hasData.value = false;
      } finally {
        currentRequest = null;
        loading.value = false;
      }
    };
    
    // 优化的图表初始化
    const initChart = () => {
      if (!chartRef.value || !historyData.value.length) return;
      
      try {
        // 如果图表已经存在，销毁它
        if (chart.value) {
          chart.value.dispose();
          chart.value = null;
        }
        
        // 创建新图表，启用性能优化
        chart.value = echarts.init(chartRef.value, null, {
          renderer: 'canvas',
          useDirtyRect: true // 启用脏矩形优化
        });
        
        // 预处理数据，避免在渲染时重复计算
        const processedData = historyData.value.map(item => {
          const date = new Date(item.date);
          return {
            date: `${date.getMonth() + 1}/${date.getDate()}`,
            totalAssets: Number(item.totalAssets) || 0,
            totalInvestment: Number(item.totalInvestment) || 0,
            totalProfit: Number(item.totalProfit) || 0
          };
        });
        
        const dates = processedData.map(item => item.date);
        const totalAssets = processedData.map(item => item.totalAssets);
        const totalInvestment = processedData.map(item => item.totalInvestment);
        const totalProfit = processedData.map(item => item.totalProfit);
        
        // 优化的图表配置（删除拖动条，提升性能）
        const option = {
          animation: false, // 禁用动画提升性能
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'line',
              lineStyle: {
                color: '#1890ff',
                width: 1,
                type: 'dashed'
              }
            },
            formatter: function(params) {
              let result = `<div style="font-weight:bold;margin-bottom:4px;">${params[0].axisValue}</div>`;
              params.forEach(param => {
                const value = param.value.toFixed(2);
                const color = param.seriesName === '总收益' ? 
                  (param.value >= 0 ? '#52c41a' : '#ff4d4f') : 
                  param.color;
                
                result += `<div style="margin:2px 0;">`;
                result += `<span style="display:inline-block;margin-right:8px;border-radius:50%;width:8px;height:8px;background-color:${color};"></span>`;
                result += `${param.seriesName}: <span style="font-weight:bold;">$${value}</span></div>`;
              });
              return result;
            }
          },
          legend: {
            data: ['总资产', '总投入', '总收益'],
            bottom: 10,
            itemGap: 20,
            textStyle: {
              fontSize: 12
            }
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '50px',
            top: '20px',
            containLabel: true
          },
          xAxis: {
            type: 'category',
            boundaryGap: false,
            data: dates,
            axisLabel: {
              interval: function(index) {
                // 智能显示标签，避免重叠
                const totalPoints = dates.length;
                if (totalPoints <= 7) return true;
                if (totalPoints <= 15) return index % 2 === 0;
                if (totalPoints <= 30) return index % Math.ceil(totalPoints / 6) === 0;
                return index % Math.ceil(totalPoints / 5) === 0;
              },
              fontSize: 11,
              color: '#666'
            },
            axisLine: {
              lineStyle: { color: '#e8e8e8' }
            },
            axisTick: {
              show: false
            }
          },
          yAxis: {
            type: 'value',
            axisLabel: {
              formatter: '${value}',
              fontSize: 11,
              color: '#666'
            },
            axisLine: {
              show: false
            },
            axisTick: {
              show: false
            },
            splitLine: {
              lineStyle: {
                color: '#f0f0f0',
                type: 'dashed'
              }
            }
          },
          series: [
            {
              name: '总资产',
              type: 'line',
              data: totalAssets,
              symbol: 'circle',
              symbolSize: 4,
              showSymbol: false,
              itemStyle: { color: '#1890ff' },
              lineStyle: { width: 2, color: '#1890ff' },
              emphasis: {
                focus: 'series',
                itemStyle: { borderWidth: 2, borderColor: '#fff' }
              }
            },
            {
              name: '总投入',
              type: 'line',
              data: totalInvestment,
              symbol: 'circle',
              symbolSize: 4,
              showSymbol: false,
              itemStyle: { color: '#722ed1' },
              lineStyle: { width: 2, color: '#722ed1' },
              emphasis: {
                focus: 'series',
                itemStyle: { borderWidth: 2, borderColor: '#fff' }
              }
            },
            {
              name: '总收益',
              type: 'line',
              data: totalProfit,
              symbol: 'circle',
              symbolSize: 4,
              showSymbol: false,
              itemStyle: {
                color: function(params) {
                  return params.value >= 0 ? '#52c41a' : '#ff4d4f';
                }
              },
              lineStyle: {
                width: 2,
                color: function(params) {
                  return params.value >= 0 ? '#52c41a' : '#ff4d4f';
                }
              },
              emphasis: {
                focus: 'series',
                itemStyle: { borderWidth: 2, borderColor: '#fff' }
              }
            }
          ]
        };
        
        // 设置图表选项
        chart.value.setOption(option, true); // true表示不合并，直接替换
        
      } catch (err) {
        console.error('图表初始化失败:', err);
        error.value = '图表渲染失败';
      }
    };
    
    // 窗口大小变化处理
    let resizeTimer = null;
    const handleResize = () => {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (chart.value && !chart.value.isDisposed()) {
          chart.value.resize();
        }
      }, 100);
    };
    
    // 切换时间周期
    const changePeriod = (days) => {
      selectedPeriod.value = days;
      fetchHistoryData(days);
    };
    
    // 监听刷新触发器
    watch(() => props.refreshTrigger, () => {
      if (props.refreshTrigger > 0) {
        // 清除缓存，强制刷新
        dataCache.clear();
        fetchHistoryData(selectedPeriod.value);
      }
    });
    
    // 组件挂载时的初始化
    onMounted(() => {
      // 添加窗口大小变化监听
      window.addEventListener('resize', handleResize);
      
      // 获取初始数据
      fetchHistoryData(selectedPeriod.value);
    });
    
    // 组件卸载时的清理
    onUnmounted(() => {
      // 取消正在进行的请求
      if (currentRequest) {
        currentRequest.cancel && currentRequest.cancel();
      }
      
      // 清理图表
      if (chart.value) {
        chart.value.dispose();
        chart.value = null;
      }
      
      // 移除事件监听
      window.removeEventListener('resize', handleResize);
      
      // 清理定时器
      if (resizeTimer) {
        clearTimeout(resizeTimer);
      }
      
      // 清理缓存
      dataCache.clear();
    });
    
    return {
      chartRef,
      loading,
      error,
      selectedPeriod,
      periods,
      hasData,
      changePeriod
    };
  }
}
</script>

<style scoped>
.asset-trend {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.period-selector {
  display: flex;
  gap: 8px;
}

.period-btn {
  padding: 4px 10px;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.3s;
}

.period-btn:hover {
  color: #1890ff;
  border-color: #1890ff;
}

.period-btn.active {
  color: #fff;
  background: #1890ff;
  border-color: #1890ff;
}

.chart-container {
  height: 300px;
  position: relative;
}

.chart {
  width: 100%;
  height: 100%;
}

.loading-spinner {
  display: inline-block;
  width: 30px;
  height: 30px;
  border: 3px solid rgba(24, 144, 255, 0.2);
  border-radius: 50%;
  border-top-color: #1890ff;
  animation: spin 1s ease-in-out infinite;
  position: absolute;
  top: 50%;
  left: 50%;
  margin-top: -15px;
  margin-left: -15px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  color: #ff4d4f;
  text-align: center;
  padding: 20px;
}

.no-data {
  color: #999;
  text-align: center;
  padding: 20px;
}
</style>