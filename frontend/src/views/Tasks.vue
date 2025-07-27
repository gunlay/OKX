<template>
  <div class="tasks">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-row">
        <select v-model="filters.symbol" class="filter-select">
          <option value="">全部币种</option>
          <option v-for="coin in availableCoins" :key="coin" :value="coin">{{ coin }}</option>
        </select>
        
        <select v-model="filters.status" class="filter-select">
          <option value="">全部状态</option>
          <option value="enabled">有效</option>
          <option value="disabled">无效</option>
        </select>
        
        <select v-model="filters.direction" class="filter-select">
          <option value="">全部方向</option>
          <option value="buy">买入</option>
          <option value="sell">卖出</option>
        </select>
      </div>
      
      <button class="create-btn" @click="showCreateModal = true">
        新建任务
      </button>
    </div>

    <!-- 任务列表 -->
    <div class="task-list" v-if="!loading && tasks.length > 0">
      <div v-for="task in filteredTasks" :key="task.id" class="task-item">
        <div class="task-header">
          <span class="task-title">{{ task.title || `任务${task.id}` }}</span>
          <span class="task-status" :class="task.status">
            {{ task.status === 'enabled' ? '有效' : '无效' }}
          </span>
        </div>
        
        <div class="task-content">
          <div class="task-info">
            <div class="info-row">
              <span class="label">币种:</span>
              <span class="value">{{ task.symbol }}</span>
            </div>
            <div class="info-row">
              <span class="label">金额:</span>
              <span class="value">${{ task.amount }}</span>
            </div>
            <div class="info-row">
              <span class="label">方向:</span>
              <span class="value" :class="task.direction || 'buy'">
                {{ task.direction === 'sell' ? '卖出' : '买入' }}
              </span>
            </div>
            <div class="info-row">
              <span class="label">周期:</span>
              <span class="value">{{ formatFrequency(task) }}</span>
            </div>
          </div>
          
          <div class="task-actions">
            <button class="action-btn edit" @click="editTask(task)">编辑</button>
            <button class="action-btn delete" @click="deleteTask(task.id)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && tasks.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <p>暂无定投任务</p>
      <button class="btn primary" @click="showCreateModal = true">创建第一个任务</button>
    </div>

    <!-- 新建/编辑任务弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>{{ editingTask ? '编辑任务' : '新建任务' }}</h3>
          <button class="close-btn" @click="showCreateModal = false">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>任务标题</label>
            <input type="text" v-model="taskForm.title" placeholder="输入任务标题" />
          </div>
          
          <div class="form-group">
            <label>币种</label>
            <select v-model="taskForm.symbol" required>
              <option value="">请选择币种</option>
              <option v-for="coin in availableCoins" :key="coin" :value="coin">{{ coin }}</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>金额 (USDT)</label>
            <input type="number" v-model="taskForm.amount" placeholder="输入金额" required min="0.01" step="0.01" />
          </div>
          
          <div class="form-group">
            <label>方向</label>
            <div class="radio-group">
              <label>
                <input type="radio" v-model="taskForm.direction" value="buy" />
                买入
              </label>
              <label>
                <input type="radio" v-model="taskForm.direction" value="sell" />
                卖出
              </label>
            </div>
          </div>
          
          <div class="form-group">
            <label>频率</label>
            <select v-model="taskForm.frequency" required>
              <option value="">请选择频率</option>
              <option value="daily">每天</option>
              <option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </div>
          
          <!-- 每周选择 -->
          <div class="form-group" v-if="taskForm.frequency === 'weekly'">
            <label>星期几</label>
            <select v-model="taskForm.day_of_week" required>
              <option value="0">周一</option>
              <option value="1">周二</option>
              <option value="2">周三</option>
              <option value="3">周四</option>
              <option value="4">周五</option>
              <option value="5">周六</option>
              <option value="6">周日</option>
            </select>
          </div>
          
          <!-- 每月选择 -->
          <div class="form-group" v-if="taskForm.frequency === 'monthly'">
            <label>每月日期</label>
            <div class="month-days">
              <div 
                v-for="day in 31" 
                :key="day" 
                class="day-item" 
                :class="{ selected: isMonthDaySelected(day) }"
                @click="toggleMonthDay(day)"
              >
                {{ day }}
              </div>
            </div>
          </div>
          
          <div class="form-group">
            <label>时间</label>
            <input type="time" v-model="taskForm.time" required />
          </div>
          
          <div v-if="formError" class="form-error">
            {{ formError }}
          </div>
          
          <div class="form-actions">
            <button 
              class="btn primary" 
              @click="saveTask" 
              :disabled="saving"
            >
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="btn secondary" @click="showCreateModal = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { dcaApi, configApi } from '../api.js';

export default {
  name: 'Tasks',
  data() {
    return {
      tasks: [],
      availableCoins: [],
      loading: false,
      showCreateModal: false,
      editingTask: null,
      saving: false,
      formError: '',
      filters: {
        symbol: '',
        status: '',
        direction: ''
      },
      taskForm: {
        title: '',
        symbol: '',
        amount: '',
        direction: 'buy',
        frequency: '',
        day_of_week: null,
        month_days: [],
        time: ''
      }
    }
  },
  computed: {
    filteredTasks() {
      return this.tasks.filter(task => {
        if (this.filters.symbol && task.symbol !== this.filters.symbol) return false
        if (this.filters.status && task.status !== this.filters.status) return false
        if (this.filters.direction && (task.direction || 'buy') !== this.filters.direction) return false
        return true
      })
    }
  },
  async mounted() {
    this.loadTasks();
    this.loadCoins();
  },
  methods: {
    async loadTasks() {
      try {
        this.loading = true;
        const response = await dcaApi.getPlans();
        this.tasks = response.data;
      } catch (error) {
        console.error('加载任务失败:', error);
        alert('加载任务失败: ' + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },
    
    async loadCoins() {
      try {
        const response = await configApi.getCoinConfig();
        this.availableCoins = response.data;
        
        // 如果没有配置币种，添加默认币种
        if (!this.availableCoins || this.availableCoins.length === 0) {
          this.availableCoins = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT'];
        }
      } catch (error) {
        console.error('加载币种配置失败:', error);
        this.availableCoins = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT'];
      }
    },
    
    formatFrequency(task) {
      if (task.frequency === 'daily') {
        return `每日 ${task.time}`;
      } else if (task.frequency === 'weekly') {
        const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        const day = weekdays[task.day_of_week] || '未知';
        return `每周${day} ${task.time}`;
      } else if (task.frequency === 'monthly') {
        if (task.month_days && task.month_days.length > 0) {
          const days = JSON.parse(task.month_days).sort((a, b) => a - b).join('号,');
          return `每月${days}号 ${task.time}`;
        }
        return `每月 ${task.time}`;
      }
      return task.frequency;
    },
    
    isMonthDaySelected(day) {
      return this.taskForm.month_days.includes(day);
    },
    
    toggleMonthDay(day) {
      const index = this.taskForm.month_days.indexOf(day);
      if (index > -1) {
        this.taskForm.month_days.splice(index, 1);
      } else {
        this.taskForm.month_days.push(day);
      }
      // 排序
      this.taskForm.month_days.sort((a, b) => a - b);
    },
    
    editTask(task) {
      this.editingTask = task;
      this.taskForm = { 
        title: task.title || '',
        symbol: task.symbol,
        amount: task.amount,
        direction: task.direction || 'buy',
        frequency: task.frequency,
        day_of_week: task.day_of_week !== undefined ? String(task.day_of_week) : null,
        month_days: task.month_days ? JSON.parse(task.month_days) : [],
        time: task.time
      };
      this.showCreateModal = true;
    },
    
    async deleteTask(id) {
      if (confirm('确定要删除这个任务吗？')) {
        try {
          await dcaApi.deletePlan(id);
          this.tasks = this.tasks.filter(task => task.id !== id);
        } catch (error) {
          console.error('删除任务失败:', error);
          alert('删除任务失败: ' + (error.response?.data?.detail || error.message));
        }
      }
    },
    
    async saveTask() {
      // 表单验证
      if (!this.taskForm.symbol || !this.taskForm.amount || !this.taskForm.direction || 
          !this.taskForm.frequency || !this.taskForm.time) {
        this.formError = '请填写完整信息';
        return;
      }
      
      if (this.taskForm.frequency === 'weekly' && this.taskForm.day_of_week === null) {
        this.formError = '请选择星期几';
        return;
      }
      
      if (this.taskForm.frequency === 'monthly' && this.taskForm.month_days.length === 0) {
        this.formError = '请选择每月执行日期';
        return;
      }
      
      this.formError = '';
      this.saving = true;
      
      try {
        // 准备提交数据
        const planData = {
          title: this.taskForm.title,
          symbol: this.taskForm.symbol,
          amount: parseFloat(this.taskForm.amount),
          frequency: this.taskForm.frequency,
          day_of_week: this.taskForm.frequency === 'weekly' ? parseInt(this.taskForm.day_of_week) : null,
          month_days: this.taskForm.frequency === 'monthly' ? JSON.stringify(this.taskForm.month_days) : null,
          time: this.taskForm.time,
          direction: this.taskForm.direction
        };
        
        let response;
        if (this.editingTask) {
          // 编辑任务
          response = await dcaApi.updatePlan(this.editingTask.id, planData);
          const index = this.tasks.findIndex(task => task.id === this.editingTask.id);
          if (index !== -1) {
            this.tasks[index] = response.data;
          }
        } else {
          // 新建任务
          response = await dcaApi.createPlan(planData);
          this.tasks.push(response.data);
        }
        
        this.showCreateModal = false;
        this.editingTask = null;
        this.resetForm();
      } catch (error) {
        console.error('保存任务失败:', error);
        this.formError = '保存失败: ' + (error.response?.data?.detail || error.message);
      } finally {
        this.saving = false;
      }
    },
    
    resetForm() {
      this.taskForm = {
        title: '',
        symbol: '',
        amount: '',
        direction: 'buy',
        frequency: '',
        day_of_week: null,
        month_days: [],
        time: ''
      };
      this.formError = '';
    }
  }
}
</script>

<style scoped>
.tasks {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.filter-bar {
  background: white;
  border-radius: 12px;
  padding: 15px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filter-row {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.filter-select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background-color: #f9f9f9;
}

.create-btn {
  width: 100%;
  padding: 10px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.task-item {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.task-header {
  padding: 12px 15px;
  background-color: #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-title {
  font-weight: bold;
  font-size: 16px;
}

.task-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.task-status.enabled {
  background-color: #52c41a;
  color: white;
}

.task-status.disabled {
  background-color: #ff4d4f;
  color: white;
}

.task-content {
  padding: 15px;
  display: flex;
  justify-content: space-between;
}

.task-info {
  flex: 1;
}

.info-row {
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.info-row .label {
  width: 60px;
  color: #666;
}

.info-row .value {
  font-weight: 500;
}

.value.buy {
  color: #52c41a;
}

.value.sell {
  color: #ff4d4f;
}

.task-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
}

.action-btn.edit {
  background-color: #1890ff;
  color: white;
}

.action-btn.delete {
  background-color: #ff4d4f;
  color: white;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 40px 0;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #1890ff;
  border-radius: 50%;
  margin: 0 auto 20px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  padding: 15px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
}

.modal-body {
  padding: 15px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.form-group input, .form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.radio-group {
  display: flex;
  gap: 15px;
}

.radio-group label {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.month-days {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.day-item {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.day-item.selected {
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

.form-error {
  color: #ff4d4f;
  margin-bottom: 15px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.btn.primary {
  background-color: #1890ff;
  color: white;
}

.btn.secondary {
  background-color: #f0f0f0;
  color: #333;
}

.btn[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
}
</style> 