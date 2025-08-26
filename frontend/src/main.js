import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'

// 路由配置 - 使用懒加载优化打包
const routes = [
  { path: '/', component: () => import('./views/Home.vue') },
  { path: '/market', component: () => import('./views/Market.vue') },
  { path: '/transactions', component: () => import('./views/Transactions.vue') },
  { path: '/tasks', component: () => import('./views/Tasks.vue') },
  { path: '/settings', component: () => import('./views/Settings.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

createApp(App).use(router).mount('#app')
