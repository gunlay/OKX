import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

export const getPlans = () => axios.get(`${API_BASE}/api/dca-plan`).then(res => res.data);
export const createPlan = (data) => axios.post(`${API_BASE}/api/dca-plan`, data).then(res => res.data);
export const updatePlan = (id, data) => axios.put(`${API_BASE}/api/dca-plan/${id}`, data).then(res => res.data);
export const deletePlan = (id) => axios.delete(`${API_BASE}/api/dca-plan/${id}`).then(res => res.data); 