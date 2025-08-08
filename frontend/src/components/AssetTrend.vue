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
    
    <!-- 风险指标 -->
    <div v-if="hasData && (riskMetrics.maxDrawdown > 0 || riskMetrics.volatility > 0 || riskMetrics.sharpeRatio)" class="risk-metrics">
      <div class="metric-item">
        <span class="metric-label">最大回撤:</span>
        <span class="metric-value">{{ formatPercentage(riskMetrics.maxDrawdown) }}</span>
        <span class="metric-tooltip" title="最大回撤是指投资组合从峰值到谷值的最大跌幅，是衡量投资风险的重要指标">ℹ️</span>
      </div>
      <div class="metric-item">
        <span class="metric-label">年化波动率:</span>
        <span class="metric-value">{{ formatPercentage(riskMetrics.volatility) }}</span>
        <span class="metric-tooltip" title="波动率是衡量资产价格变化幅度的指标，数值越大表示价格波动越剧烈">ℹ️</span>
      </div>
      <div class="metric-item" v-if="riskMetrics.sharpeRatio !== undefined">
        <span class="metric-label">夏普比率:</span>
        <span class="metric-value" :class="{ 'positive': riskMetrics.sharpeRatio > 0, 'negative': riskMetrics.sharpeRatio < 0 }">
          {{ riskMetrics.sharpeRatio.toFixed(2) }}
        </span>
        <span class="metric-tooltip" title="夏普比率表示每单位风险所获得的超额收益，数值越高表示风险调整后的收益越好">ℹ️</span>
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
import { ref, onMounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { assetApi } from '../api.js';

// 注册必要的组件
echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
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
    
    // 风险指标数据
    const riskMetrics = ref({
      maxDrawdown: 0,
      volatility: 0,
      sharpeRatio: 0
    });
    
    // 获取历史数据
    const fetchHistoryData = async (days) => {
      try {
        loading.value = true;
        error.value = '';
        
        const response = await assetApi.getHistory(days, true); // 请求包含风险指标的数据
        
        if (response.data.history) {
          // 新的API格式，包含历史数据和风险指标
          historyData.value = response.data.history;
          riskMetrics.value = response.data.metrics || { maxDrawdown: 0, volatility: 0 };
        } else {
          // 旧的API格式，只有历史数据
          historyData.value = response.data;
        }
        
        hasData.value = historyData.value && historyData.value.length > 0;
        
        if (hasData.value) {
          nextTick(() => {
            initChart();
          });
        }
      } catch (err) {
        console.error('获取资产历史数据失败:', err);
        error.value = '获取资产历史数据失败: ' + (err.response?.data?.detail || err.message);
      } finally {
        loading.value = false;
      }
    };
    
    // 初始化图表
    const initChart = () => {
      if (!chartRef.value) return;
      
      // 如果图表已经存在，销毁它
      if (chart.value) {
        chart.value.dispose();
      }
      
      // 创建新图表
      chart.value = echarts.init(chartRef.value);
      
      // 处理数据
      const dates = historyData.value.map(item => {
        const date = new Date(item.date);
        return `${date.getMonth() + 1}/${date.getDate()}`;
      });
      
      const totalAssets = historyData.value.map(item => item.totalAssets);
      const totalInvestment = historyData.value.map(item => item.totalInvestment);
      const totalProfit = historyData.value.map(item => item.totalProfit);
      
      // 设置图表选项
      const option = {
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            let result = params[0].axisValue + '<br/>';
            params.forEach(param => {
              const value = param.value.toFixed(2);
              const color = param.seriesName === '总收益' ? 
                (param.value >= 0 ? '#52c41a' : '#ff4d4f') : 
                param.color;
              
              result += `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>`;
              result += `${param.seriesName}: $${value}<br/>`;
            });
            return result;
          }
        },
        legend: {
          data: ['总资产', '总投入', '总收益'],
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '60px',
          top: '30px',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: dates,
          axisLabel: {
            interval: Math.floor(dates.length / 7) // 根据数据量调整显示间隔
          }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: '${value}'
          }
        },
        series: [
          {
            name: '总资产',
            type: 'line',
            data: totalAssets,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: {
              color: '#1890ff'
            },
            lineStyle: {
              width: 2
            }
          },
          {
            name: '总投入',
            type: 'line',
            data: totalInvestment,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: {
              color: '#722ed1'
            },
            lineStyle: {
              width: 2
            }
          },
          {
            name: '总收益',
            type: 'line',
            data: totalProfit,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: {
              color: function(params) {
                return params.value >= 0 ? '#52c41a' : '#ff4d4f';
              }
            },
            lineStyle: {
              width: 2,
              color: function(params) {
                const colorStops = [];
                for (let i = 0; i < totalProfit.length; i++) {
                  colorStops.push({
                    offset: i / (totalProfit.length - 1),
                    color: totalProfit[i] >= 0 ? '#52c41a' : '#ff4d4f'
                  });
                }
                return {
                  type: 'linear',
                  x: 0,
                  y: 0,
                  x2: 1,
                  y2: 0,
                  colorStops: colorStops
                };
              }
            }
          }
        ],
        dataZoom: [
          {
            type: 'inside',
            start: 0,
            end: 100
          },
          {
            type: 'slider',
            start: 0,
            end: 100
          }
        ]
      };
      
      // 设置图表
      chart.value.setOption(option);
      
      // 响应窗口大小变化
      window.addEventListener('resize', () => {
        chart.value && chart.value.resize();
      });
    };
    
    // 切换时间周期
    const changePeriod = (days) => {
      selectedPeriod.value = days;
      fetchHistoryData(days);
    };
    
    // 监听刷新触发器
    watch(() => props.refreshTrigger, () => {
      fetchHistoryData(selectedPeriod.value);
    });
    
    // 组件挂载时获取数据
    onMounted(() => {
      fetchHistoryData(selectedPeriod.value);
    });
    
    // 格式化百分比
    const formatPercentage = (value) => {
      if (!value && value !== 0) return '0.00%';
      return `${(value * 100).toFixed(2)}%`;
    };
    
    return {
      chartRef,
      loading,
      error,
      selectedPeriod,
      periods,
      hasData,
      riskMetrics,
      changePeriod,
      formatPercentage
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

.risk-metrics {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding: 10px 15px;
  background-color: #f9f9f9;
  border-radius: 6px;
  font-size: 14px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.metric-label {
  color: #666;
}

.metric-value {
  font-weight: 600;
  color: #333;
}

.metric-tooltip {
  cursor: help;
  color: #1890ff;
}

.positive {
  color: #52c41a;
}

.negative {
  color: #ff4d4f;
}
</style>