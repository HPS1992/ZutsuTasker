import axios from 'axios';

const API_URL = (typeof process !== 'undefined' && process.env && process.env.EXPO_PUBLIC_API_URL) ? process.env.EXPO_PUBLIC_API_URL : 'https://zutsu-tasker.vercel.app/api';
export const api = axios.create({ baseURL: API_URL, timeout: 15000, headers: { 'Content-Type': 'application/json' } });

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.error;
    if (typeof message === 'string') return message;
    if (!error.response) return 'No se pudo conectar con el servidor. Comprueba tu conexión e inténtalo de nuevo.';
  }
  return error instanceof Error ? error.message : 'No se pudo completar la operación';
}

export const getTasks = async () => (await api.get(`/tasks`)).data;
export const createTask = async (data: any) => (await api.post(`/tasks`, data)).data;
export const completeTask = async (taskId: string, photoUri?: string) => (await api.post(`/tasks/${taskId}/complete`, { photoUri })).data;
export const approveTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/approve`)).data;
export const claimTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/claim`)).data;
export const stealTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/steal`)).data;

export const getRewards = async () => (await api.get(`/rewards`)).data;
export const createReward = async (data: any) => (await api.post(`/rewards`, data)).data;
export const deleteReward = async (id: string) => (await api.delete(`/rewards/${id}`)).data;
export const redeemReward = async (id: string) => (await api.post(`/rewards/${id}/redeem`)).data;

export const createGroup = async (name: string) => (await api.post('/group/create', { name })).data;
export const joinGroup = async (groupId: string) => (await api.post('/group/join', { groupId })).data;
export const getMembers = async () => (await api.get('/group/members')).data;
export const kickMember = async (userId: string) => (await api.delete(`/group/members/${userId}`)).data;
export const transferPoints = async (to_user_id: string, amount: string) => (await api.post('/users/transfer', { to_user_id, amount })).data;

export const getEquityStats = async () => (await api.get('/stats/equity')).data;

export const getRedemptions = async () => (await api.get('/rewards/redemptions')).data;
export const completeRedemption = async (id: string) => (await api.post(`/rewards/redemptions/${id}/complete`)).data;

export const getTasksHistory = async () => (await api.get('/tasks/history')).data;
export const getRewardsHistory = async () => (await api.get('/rewards/history')).data;
