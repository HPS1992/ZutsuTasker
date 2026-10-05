import { create } from 'zustand';
import { getTasks, completeTask as completeTaskApi, approveTask as approveTaskApi, claimTask as claimTaskApi, stealTask as stealTaskApi, api, getApiError } from '../services/api';
import { Alert } from 'react-native';
import { triggerWowEffect, triggerStealEffect } from '../utils/SoundHaptics';

interface TaskState {
  tasks: any[];
  loading: boolean;
  error: string | null;
  fetchTasks: () => Promise<void>;
  completeTask: (id: string, photoUri?: string) => Promise<void>;
  approveTask: (id: string) => Promise<void>;
  claimTask: (id: string) => Promise<void>;
  stealTask: (id: string) => Promise<void>;
  updateTask: (id: string, data: any) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  loading: false,
  error: null,
  fetchTasks: async () => {
    set({ loading: true, error: null });
    try { const data = await getTasks(); set({ tasks: data }); }
    catch (error) { set({ error: getApiError(error) }); }
    finally { set({ loading: false }); }
  },
  completeTask: async (id: string, photoUri?: string) => {
    const res = await completeTaskApi(id, photoUri);
    if (!photoUri) await triggerWowEffect();
    else alert(res.message);
    const updated = await getTasks(); set({ tasks: updated });
  },
  approveTask: async (id: string) => {
    await approveTaskApi(id);
    await triggerWowEffect();
    const updated = await getTasks(); set({ tasks: updated });
  },
  claimTask: async (id: string) => {
    await claimTaskApi(id);
    const updated = await getTasks(); set({ tasks: updated });
  },
  stealTask: async (id: string) => {
    try {
      const res = await stealTaskApi(id);
      await triggerStealEffect();
      alert('¡Robo completado! ' + res.message);
      const updated = await getTasks(); set({ tasks: updated });
    } catch(e: any) { alert('Error al robar: ' + (e.response?.data?.error || e.message)); }
  },
  updateTask: async (id: string, data: any) => {
    await api.put(`/tasks/${id}`, data);
    const updated = await getTasks(); set({ tasks: updated });
  },
  deleteTask: async (id: string) => {
    await api.delete(`/tasks/${id}`);
    const updated = await getTasks(); set({ tasks: updated });
  }
}));
