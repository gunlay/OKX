<template>
  <div class="tasks">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-row">
        <select v-model="filters.symbol" class="filter-select">
          <option value="">全部币种</option>
          <option value="BTC-USDT">BTC-USDT</option>
          <option value="ETH-USDT">ETH-USDT</option>
          <option value="BNB-USDT">BNB-USDT</option>
        </select>
        
        <select v-model="filters.status" class="filter-select">
          <option value="">全部状态</option>
          <option value="active">有效</option>
          <option value="inactive">无效</option>
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
    <div class="task-list">
      <div v-for="task in filteredTasks" :key="task.id" class="task-item">
        <div class="task-header">
          <span class="task-id">#{{ task.id }}</span>
          <span class="task-status" :class="task.status">
            {{ task.status === 'active' ? '有效' : '无效' }}
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
              <span class="value" :class="task.direction">
                {{ task.direction === 'buy' ? '买入' : '卖出' }}
              </span>
            </div>
            <div class="info-row">
              <span class="label">周期:</span>
              <span class="value">{{ task.frequency }}</span>
            </div>
          </div>
          
          <div class="task-actions">
            <button class="action-btn edit" @click="editTask(task)">编辑</button>
            <button class="action-btn delete" @click="deleteTask(task.id)">删除</button>
          </div>
        </div>
      </div>
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
            <label>币种</label>
            <select v-model="taskForm.symbol" required>
              <option value="">请选择币种</option>
              <option value="BTC-USDT">BTC-USDT</option>
              <option value="ETH-USDT">ETH-USDT</option>
              <option value="BNB-USDT">BNB-USDT</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>金额 (USDT)</label>
            <input type="number" v-model="taskForm.amount" min="0.01" step="0.01" required />
          </div>
          
          <div class="form-group">
            <label>方向</label>
            <select v-model="taskForm.direction" required>
              <option value="">请选择方向</option>
              <option value="buy">买入</option>
              <option value="sell">卖出</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>频率</label>
            <select v-model="taskForm.frequency" required>
              <option value="">请选择频率</option>
              <option value="daily">每日</option>
              <option value="weekly">每周</option>
              <option value="monthly">每月</option>
            </select>
          </div>
          
          <div v-if="taskForm.frequency === 'weekly'" class="form-group">
            <label>星期几</label>
            <select v-model="taskForm.dayOfWeek">
              <option value="0">周一</option>
              <option value="1">周二</option>
              <option value="2">周三</option>
              <option value="3">周四</option>
              <option value="4">周五</option>
              <option value="5">周六</option>
              <option value="6">周日</option>
            </select>
          </div>
          
          <div class="form-group">
            <label>执行时间</label>
            <input type="time" v-model="taskForm.time" required />
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn secondary" @click="showCreateModal = false">取消</button>
          <button class="btn primary" @click="saveTask">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Tasks',
  data() {
    return {
      filters: {
        symbol: '',
        status: '',
        direction: ''
      },
      showCreateModal: false,
      editingTask: null,
      taskForm: {
        symbol: '',
        amount: '',
        direction: '',
        frequency: '',
        dayOfWeek: null,
        time: ''
      },
      tasks: [
        {
          id: 1,
          symbol: 'BTC-USDT',
          amount: 100,
          direction: 'buy',
          status: 'active',
          frequency: 'weekly',
          dayOfWeek: 1,
          time: '10:00'
        },
        {
          id: 2,
          symbol: 'ETH-USDT',
          amount: 50,
          direction: 'buy',
          status: 'active',
          frequency: 'daily',
          time: '14:00'
        }
      ]
    }
  },
  computed: {
    filteredTasks() {
      return this.tasks.filter(task => {
        if (this.filters.symbol && task.symbol !== this.filters.symbol) return false
        if (this.filters.status && task.status !== this.filters.status) return false
        if (this.filters.direction && task.direction !== this.filters.direction) return false
        return true
      })
    }
  },
  methods: {
    editTask(task) {
      this.editingTask = task
      this.taskForm = { ...task }
      this.showCreateModal = true
    },
    
    deleteTask(id) {
      if (confirm('确定要删除这个任务吗？')) {
        this.tasks = this.tasks.filter(task => task.id !== id)
      }
    },
    
    saveTask() {
      if (!this.taskForm.symbol || !this.taskForm.amount || !this.taskForm.direction || 
          !this.taskForm.frequency || !this.taskForm.time) {
        alert('请填写完整信息')
        return
      }
      
      if (this.editingTask) {
        // 编辑任务
        const index = this.tasks.findIndex(task => task.id === this.editingTask.id)
        this.tasks[index] = { ...this.editingTask, ...this.taskForm }
      } else {
        // 新建任务
        const newTask = {
          id: Date.now(),
          ...this.taskForm,
          status: 'active'
        }
        this.tasks.push(newTask)
      }
      
      this.showCreateModal = false
      this.editingTask = null
      this.resetForm()
    },
    
    resetForm() {
      this.taskForm = {
        symbol: '',
        amount: '',
        direction: '',
        frequency: '',
        dayOfWeek: null,
        time: ''
      }
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
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
}

.create-btn {
  width: 100%;
  padding: 12px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.task-item {
  background: white;
  border-radius: 12px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-id {
  font-weight: 600;
  color: #333;
}

.task-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.task-status.active {
  background: #f6ffed;
  color: #52c41a;
}

.task-status.inactive {
  background: #fff2f0;
  color: #ff4d4f;
}

.task-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.task-info {
  flex: 1;
}

.info-row {
  display: flex;
  margin-bottom: 8px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.label {
  width: 60px;
  color: #666;
  font-size: 14px;
}

.value {
  color: #333;
  font-size: 14px;
}

.value.buy {
  color: #52c41a;
}

.value.sell {
  color: #ff4d4f;
}

.task-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.action-btn.edit {
  background: #1890ff;
  color: white;
}

.action-btn.delete {
  background: #ff4d4f;
  color: white;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h3 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #333;
  font-weight: 500;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
}

.modal-footer {
  display: flex;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #f0f0f0;
}

.btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn.primary {
  background: #1890ff;
  color: white;
}

.btn.secondary {
  background: #f0f0f0;
  color: #333;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .tasks {
    padding: 15px;
  }
  
  .filter-row {
    flex-direction: column;
  }
  
  .task-content {
    flex-direction: column;
    gap: 15px;
  }
  
  .task-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style> 