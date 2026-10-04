import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

if "requires_photo" not in schema:
    schema = schema.replace(
        "end_date       DateTime?",
        "end_date       DateTime?\n  requires_photo Boolean        @default(false)"
    )
    schema = schema.replace(
        "is_on_vacation Boolean  @default(false)",
        "is_on_vacation Boolean  @default(false)\n  is_mvp         Boolean  @default(false)\n  last_completed_date DateTime?"
    )
    schema = schema.replace(
        "assigned_to      String?",
        "assigned_to      String?\n  created_at       DateTime     @default(now())\n  photo_uri        String?"
    )
with open(schema_path, "w", encoding="utf-8") as f:
    f.write(schema)


# 2. Add Haptics/Audio utility
files["mobile/src/utils/SoundHaptics.ts"] = """import * as Haptics from 'expo-haptics';
import { Audio } from 'expo-av';
import { Platform } from 'react-native';

export const triggerWowEffect = async () => {
  try {
    if (Platform.OS !== 'web') {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    }
    const { sound } = await Audio.Sound.createAsync(
      { uri: 'https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=success-1-6297.mp3' }
    );
    await sound.playAsync();
  } catch (error) {
    console.log('Audio/Haptic error ignored', error);
  }
};

export const triggerStealEffect = async () => {
  try {
    if (Platform.OS !== 'web') {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    }
  } catch (error) {}
};
"""

# 3. Update taskService for Streaks, Photo Reviews, Bounties
files["backend/src/services/taskService.ts"] = """import { PrismaClient } from '@prisma/client';
import { notificationService } from './notificationService';

const prisma = new PrismaClient();

export const taskService = {
  // Helpers
  calculateBounty(task: any, basePoints: number) {
    if (task.template.assignment_type === 'MANUAL' && !task.assigned_to) {
      const daysOld = Math.floor((new Date().getTime() - task.created_at.getTime()) / (1000 * 3600 * 24));
      if (daysOld > 0) return basePoints + (daysOld * 5); // +5 puntos por cada día ignorada
    }
    return basePoints;
  },

  async updateStreakAndMVP(groupId: string, userId: string) {
    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: userId, group_id: groupId } } });
    if (!member) return;
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    let newStreak = member.streak_days;
    if (member.last_completed_date) {
      const last = new Date(member.last_completed_date);
      const lastDay = new Date(last.getFullYear(), last.getMonth(), last.getDate());
      const diffDays = Math.floor((today.getTime() - lastDay.getTime()) / (1000 * 3600 * 24));
      
      if (diffDays === 1) newStreak += 1;
      else if (diffDays > 1) newStreak = 1;
    } else {
      newStreak = 1;
    }

    await prisma.groupMember.update({
      where: { id: member.id },
      data: { streak_days: newStreak, last_completed_date: now }
    });

    // Calcular MVP semanal (Lógica simple: el que más puntos tenga en total, 
    // en un caso real se filtra por los puntos de los últimos 7 días)
    const members = await prisma.groupMember.findMany({
      where: { group_id: groupId },
      orderBy: { total_points: 'desc' }
    });
    
    if (members.length > 0) {
      // Limpiar MVP anterior
      await prisma.groupMember.updateMany({ where: { group_id: groupId }, data: { is_mvp: false } });
      // Coronar nuevo MVP
      await prisma.groupMember.update({ where: { id: members[0].id }, data: { is_mvp: true } });
    }
  },

  async completeTask(taskId: string, userId: string, photoUri?: string) {
    const task = await prisma.taskInstance.findUnique({ where: { id: taskId }, include: { template: true, group: true } });
    if (!task || task.status === 'COMPLETED' || task.status === 'PENDING_REVIEW') throw new Error('Task unavailable');

    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } } });
    if (!member) throw new Error('Not part of group');

    if (task.template.requires_photo && !photoUri) {
      throw new Error('Esta tarea requiere foto obligatoria');
    }

    if (task.template.requires_photo && photoUri) {
      await prisma.taskInstance.update({
        where: { id: taskId },
        data: { status: 'PENDING_REVIEW', photo_uri: photoUri, assigned_to: userId }
      });
      await notificationService.notifyGroup(task.group_id, '📸 Foto a revisión', `Alguien ha subido foto para: ${task.template.title}`, userId);
      return { success: true, message: 'Foto enviada. Esperando aprobación de los compañeros.' };
    }

    // Flujo normal sin foto
    const now = new Date();
    const isOverdue = now > task.due_date;
    
    let points = this.calculateBounty(task, task.template.points);
    
    if (isOverdue && task.group.penalty_enabled && task.assigned_to) {
        const originalAssignee = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
        if (originalAssignee && !originalAssignee.is_on_vacation) {
            points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
        }
    }

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, assigned_to: userId } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } }, data: { total_points: member.total_points + points } }),
      prisma.pointsLog.create({ data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETION' } })
    ]);

    await this.updateStreakAndMVP(task.group_id, userId);
    await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);
    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien completó: ${task.template.title}`, userId);
    return { success: true, message: `Tarea completada, +${points} puntos` };
  },

  async approveTask(taskId: string, approverId: string) {
    const task = await prisma.taskInstance.findUnique({ where: { id: taskId }, include: { template: true, group: true } });
    if (!task || task.status !== 'PENDING_REVIEW' || !task.assigned_to) throw new Error('Invalid task');
    if (task.assigned_to === approverId) throw new Error('No puedes aprobar tu propia foto');

    const points = this.calculateBounty(task, task.template.points);
    const now = new Date();
    
    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } }, data: { total_points: (member?.total_points || 0) + points } }),
      prisma.pointsLog.create({ data: { user_id: task.assigned_to, group_id: task.group_id, amount: points, reason: 'TASK_APPROVED' } })
    ]);

    await this.updateStreakAndMVP(task.group_id, task.assigned_to);
    await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);
    await notificationService.notifyGroup(task.group_id, '🎉 Foto Aprobada', `Se han liberado los puntos de: ${task.template.title}`, approverId);
    return { success: true, message: 'Foto aprobada y puntos entregados' };
  },

  async stealTask(taskId: string, thiefId: string) {
    const task = await prisma.taskInstance.findUnique({ where: { id: taskId }, include: { template: true, group: true } });
    if (!task || task.status === 'COMPLETED' || task.status === 'PENDING_REVIEW') throw new Error('Task unavailable');
    if (!task.assigned_to || task.assigned_to === thiefId) throw new Error('No puedes robar esta tarea');

    const victimMember = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
    if (victimMember?.is_on_vacation) throw new Error('No puedes robarle tareas a alguien en modo vacaciones');

    const now = new Date();
    const daysOverdue = (now.getTime() - task.due_date.getTime()) / (1000 * 3600 * 24);

    if (daysOverdue < 0 || daysOverdue > 2) throw new Error('Solo puedes robar tareas vencidas hace menos de 2 días');

    const basePoints = task.template.points;
    const stolenReward = Math.floor(basePoints * 1.5);
    const stolenPenalty = Math.floor(basePoints * 0.5);

    const thiefMember = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: thiefId, group_id: task.group_id } } });
    if (!thiefMember || !victimMember) throw new Error('Group error');

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, assigned_to: thiefId } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: thiefId, group_id: task.group_id } }, data: { total_points: thiefMember.total_points + stolenReward } }),
      prisma.pointsLog.create({ data: { user_id: thiefId, group_id: task.group_id, amount: stolenReward, reason: 'TASK_STOLEN_REWARD' } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } }, data: { total_points: victimMember.total_points - stolenPenalty } }),
      prisma.pointsLog.create({ data: { user_id: task.assigned_to, group_id: task.group_id, amount: -stolenPenalty, reason: 'TASK_STOLEN_PENALTY' } })
    ]);

    await this.updateStreakAndMVP(task.group_id, thiefId);
    await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);
    await notificationService.notifyGroup(task.group_id, '🥷 ¡Tarea robada!', `Alguien ha robado: ${task.template.title}`, thiefId);
    return { success: true, message: `¡Tarea robada! +${stolenReward} pts para ti, -${stolenPenalty} pts para la víctima.` };
  },

  async spawnNextInstance(template: any, groupId: string, now: Date, originalDueDate: Date) {
    const freq = template.frequency;
    if (freq && freq !== 'ONCE') {
      const baseDate = originalDueDate > now ? originalDueDate : now;
      const nextDate = new Date(baseDate);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);
      
      if (template.end_date && nextDate > new Date(template.end_date)) return;

      let nextAssignee = null;
      if (template.assignment_type === 'RANDOM') {
        const members = await prisma.groupMember.findMany({ where: { group_id: groupId, is_on_vacation: false }, orderBy: { total_points: 'asc' } });
        if (members.length > 0) nextAssignee = members[0].user_id;
      } else if (template.assignment_type === 'FIXED') {
        nextAssignee = template.fixed_user_id;
      }

      await prisma.taskInstance.create({
        data: { template_id: template.id, group_id: groupId, due_date: nextDate, status: 'PENDING', assigned_to: nextAssignee }
      });
    }
  }
};
"""

# 4. Update taskRoutes to expose Bounties & Approval
files["backend/src/routes/taskRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { taskService } from '../services/taskService';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let tasks = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id },
      include: { template: true, assigned_user: true },
      orderBy: { due_date: 'asc' }
    });
    
    // Inyectar Bounties
    const now = new Date();
    const mappedTasks = tasks.map(t => {
      const dynamicPoints = taskService.calculateBounty(t, t.template.points);
      return {
        ...t, 
        assigned_to: t.assigned_user,
        bounty_points: dynamicPoints > t.template.points ? dynamicPoints : null
      };
    });
    
    res.json(mappedTasks);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const { title, description, points, frequency, assignment_type, fixed_user_id, start_date, end_date, requires_photo } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let initialAssignee = null;
    if (assignment_type === 'RANDOM') {
      const allMembers = await prisma.groupMember.findMany({ where: { group_id: member.group_id, is_on_vacation: false }, orderBy: { total_points: 'asc' } });
      if (allMembers.length > 0) initialAssignee = allMembers[0].user_id;
    } else if (assignment_type === 'FIXED' && fixed_user_id) initialAssignee = fixed_user_id;

    const template = await prisma.taskTemplate.create({
      data: { 
        group_id: member.group_id, title, description: description || '', points: parseInt(points) || 10, 
        frequency: frequency || 'ONCE', assignment_type: assignment_type || 'MANUAL', 
        fixed_user_id: assignment_type === 'FIXED' ? fixed_user_id : null, 
        start_date: start_date ? new Date(start_date) : new Date(), 
        end_date: end_date ? new Date(end_date) : null,
        requires_photo: !!requires_photo
      }
    });

    const instance = await prisma.taskInstance.create({
      data: { template_id: template.id, group_id: member.group_id, due_date: template.start_date, status: 'PENDING', assigned_to: initialAssignee }
    });

    res.json({ template, instance });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/complete', requireAuth, async (req, res) => {
  try {
    const { photoUri } = req.body;
    const result = await taskService.completeTask(req.params.id, req.user.id, photoUri);
    res.json(result);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/approve', requireAuth, async (req, res) => {
  try {
    const result = await taskService.approveTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/claim', requireAuth, async (req, res) => {
  try {
    const task = await prisma.taskInstance.update({ where: { id: req.params.id }, data: { assigned_to: req.user.id } });
    res.json(task);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/steal', requireAuth, async (req, res) => {
  try {
    const result = await taskService.stealTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.delete('/:id', requireAuth, async (req, res) => {
  try {
    await prisma.taskInstance.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

# 5. Update userRoutes to support Transfers
files["backend/src/routes/userRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/dashboard', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id }, include: { group: true } });
    res.json({
      id: req.user.id, name: req.user.name, reminder_time: req.user.reminder_time,
      totalPoints: member ? member.total_points : 0, streak: member ? member.streak_days : 0,
      groupName: member ? member.group.name : null, groupId: member ? member.group.id : null,
      role: member ? member.role : null, is_on_vacation: member ? member.is_on_vacation : false,
      is_mvp: member ? member.is_mvp : false
    });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/transfer', requireAuth, async (req, res) => {
  try {
    const { to_user_id, amount } = req.body;
    const numAmount = parseInt(amount);
    
    if (numAmount <= 0) return res.status(400).json({ error: 'Cantidad inválida' });

    const fromMember = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!fromMember || fromMember.total_points < numAmount) return res.status(400).json({ error: 'Puntos insuficientes' });

    const toMember = await prisma.groupMember.findFirst({ where: { user_id: to_user_id, group_id: fromMember.group_id } });
    if (!toMember) return res.status(404).json({ error: 'Destinatario no encontrado' });

    await prisma.$transaction([
      prisma.groupMember.update({ where: { id: fromMember.id }, data: { total_points: fromMember.total_points - numAmount } }),
      prisma.groupMember.update({ where: { id: toMember.id }, data: { total_points: toMember.total_points + numAmount } }),
      prisma.pointsLog.create({ data: { user_id: req.user.id, group_id: fromMember.group_id, amount: -numAmount, reason: 'TRANSFER_OUT' } }),
      prisma.pointsLog.create({ data: { user_id: to_user_id, group_id: fromMember.group_id, amount: numAmount, reason: 'TRANSFER_IN' } })
    ]);

    res.json({ success: true, message: `Has transferido ${numAmount} pts a tu compañero.` });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/settings', requireAuth, async (req, res) => {
  try {
    await prisma.user.update({ where: { id: req.user.id }, data: { reminder_time: req.body.reminder_time } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/vacation', requireAuth, async (req, res) => {
  try {
    await prisma.groupMember.updateMany({ where: { user_id: req.user.id }, data: { is_on_vacation: req.body.is_on_vacation } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

# 6. API & Store Frontend
files["mobile/src/services/api.ts"] = """import axios from 'axios';
import { Platform } from 'react-native';

const API_URL = Platform.OS === 'web' && typeof window !== 'undefined' ? `${window.location.origin}/api` : 'http://localhost:3000/api';
export const api = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } });

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
"""

files["mobile/src/store/useTaskStore.ts"] = """import { create } from 'zustand';
import { getTasks, completeTask as completeTaskApi, approveTask as approveTaskApi, claimTask as claimTaskApi, stealTask as stealTaskApi, api } from '../services/api';
import { Alert } from 'react-native';
import { triggerWowEffect, triggerStealEffect } from '../utils/SoundHaptics';

interface TaskState {
  tasks: any[];
  loading: boolean;
  fetchTasks: () => Promise<void>;
  completeTask: (id: string, photoUri?: string) => Promise<void>;
  approveTask: (id: string) => Promise<void>;
  claimTask: (id: string) => Promise<void>;
  stealTask: (id: string) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  loading: false,
  fetchTasks: async () => {
    set({ loading: true });
    try { const data = await getTasks(); set({ tasks: data }); } finally { set({ loading: false }); }
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
  deleteTask: async (id: string) => {
    await api.delete(`/tasks/${id}`);
    const updated = await getTasks(); set({ tasks: updated });
  }
}));
"""

# 7. Update TaskCard UI
files["mobile/src/components/TaskCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTaskStore } from '../store/useTaskStore';

export const TaskCard = ({ item, currentUserId, onComplete }: { item: any, currentUserId: string, onComplete: () => void }) => {
  const isCompleted = item.status === 'COMPLETED';
  const isPendingReview = item.status === 'PENDING_REVIEW';
  const now = new Date();
  const dueDate = new Date(item.due_date);
  const isOverdue = now > dueDate;
  const daysOverdue = (now.getTime() - dueDate.getTime()) / (1000 * 3600 * 24);
  
  const { deleteTask, claimTask, stealTask, approveTask } = useTaskStore();
  
  const assigneeName = item.assigned_to ? item.assigned_to.name : null;
  const isMine = item.assigned_to?.id === currentUserId;
  const isManual = item.template.assignment_type === 'MANUAL';
  
  const canSteal = !isCompleted && !isPendingReview && isOverdue && daysOverdue <= 2 && assigneeName && !isMine;
  const canClaim = !isCompleted && !isPendingReview && !assigneeName && isManual;
  const canApprove = isPendingReview && !isMine;

  const displayPoints = item.bounty_points || item.template.points;

  return (
    <View style={[styles.card, isCompleted && styles.cardCompleted]}>
      <View style={styles.content}>
        <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'}}>
           <View style={{flex: 1}}>
              <Text style={[styles.title, isCompleted && styles.textCompleted]}>{item.template.title}</Text>
              
              <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap'}}>
                 <Text style={styles.points}>
                   <Ionicons name={item.bounty_points ? 'flame' : 'star'} size={14} color={item.bounty_points ? '#EF4444' : '#F59E0B'} /> {displayPoints} pts
                 </Text>
                 
                 {item.template.frequency !== 'ONCE' && (
                   <View style={styles.badge}>
                     <Ionicons name="repeat" size={12} color="#4F46E5" />
                     <Text style={styles.badgeText}>{item.template.frequency}</Text>
                   </View>
                 )}
                 
                 <View style={[styles.badge, {backgroundColor: '#FEF3C7'}]}>
                   <Ionicons name={assigneeName ? 'person' : 'people'} size={12} color="#B45309" />
                   <Text style={[styles.badgeText, {color: '#B45309'}]}>
                      {assigneeName ? (isMine ? 'Mía' : assigneeName) : 'Pizarra Común'}
                   </Text>
                 </View>

                 {item.template.requires_photo && (
                   <View style={[styles.badge, {backgroundColor: '#FCE7F3'}]}>
                     <Ionicons name="camera" size={12} color="#DB2777" />
                     <Text style={[styles.badgeText, {color: '#DB2777'}]}>Verificación</Text>
                   </View>
                 )}
              </View>
           </View>
           {!isCompleted && !isPendingReview && (
              <TouchableOpacity onPress={() => deleteTask(item.id)} style={{padding: 8, backgroundColor:'#FEE2E2', borderRadius:8}}>
                 <Ionicons name="trash-outline" size={20} color="#EF4444" />
              </TouchableOpacity>
           )}
        </View>

        {isPendingReview && item.photo_uri && (
          <Image source={{uri: item.photo_uri}} style={styles.photoProof} />
        )}

        <View style={styles.footer}>
          <Text style={[styles.date, isOverdue && !isCompleted && !isPendingReview && styles.dateOverdue]}>
            <Ionicons name={isPendingReview ? 'time' : 'time-outline'} size={14} /> 
            {' '}{isPendingReview ? 'Pendiente de revisión' : dueDate.toLocaleDateString('es-ES')}
          </Text>
          
          <View style={{flexDirection: 'row', gap: 8}}>
            {canSteal && (
              <TouchableOpacity style={styles.stealButton} onPress={() => stealTask(item.id)}>
                <Text style={styles.stealText}>🥷 Robar (+150%)</Text>
              </TouchableOpacity>
            )}
            
            {canClaim && (
              <TouchableOpacity style={styles.claimButton} onPress={() => claimTask(item.id)}>
                <Text style={styles.claimText}>✋ ¡Me la pido!</Text>
              </TouchableOpacity>
            )}

            {canApprove && (
              <TouchableOpacity style={styles.approveButton} onPress={() => approveTask(item.id)}>
                <Text style={styles.approveText}>Aprobar Foto</Text>
                <Ionicons name="checkmark-done" size={20} color="#fff" />
              </TouchableOpacity>
            )}

            {!isCompleted && !isPendingReview && (!assigneeName || isMine || (!canSteal && !canClaim)) && (
              <TouchableOpacity style={[styles.completeButton, (!isMine && assigneeName) && {opacity: 0.5}]} onPress={onComplete} disabled={!isMine && !!assigneeName}>
                <Text style={styles.completeText}>{item.template.requires_photo ? 'Tomar Foto' : 'Completar'}</Text>
                <Ionicons name={item.template.requires_photo ? 'camera' : 'checkmark-circle'} size={20} color="#fff" />
              </TouchableOpacity>
            )}
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderRadius: 20, marginBottom: 16, overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 3 },
  cardCompleted: { backgroundColor: '#F3F4F6', opacity: 0.8 },
  content: { padding: 20 },
  title: { fontSize: 18, fontWeight: 'bold', color: '#111827', marginBottom: 8 },
  textCompleted: { textDecorationLine: 'line-through', color: '#9CA3AF' },
  points: { fontSize: 14, color: '#F59E0B', fontWeight: '700' },
  badge: { backgroundColor: '#EEF2FF', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12, flexDirection: 'row', alignItems: 'center', gap: 4 },
  badgeText: { fontSize: 12, color: '#4F46E5', fontWeight: 'bold' },
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, flexWrap: 'wrap', gap: 12 },
  date: { fontSize: 13, color: '#6B7280', fontWeight: '500' },
  dateOverdue: { color: '#EF4444', fontWeight: '700' },
  completeButton: { backgroundColor: '#10B981', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12, gap: 8 },
  completeText: { color: '#fff', fontWeight: 'bold' },
  claimButton: { backgroundColor: '#3B82F6', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12 },
  claimText: { color: '#fff', fontWeight: 'bold' },
  stealButton: { backgroundColor: '#8B5CF6', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12 },
  stealText: { color: '#fff', fontWeight: 'bold' },
  approveButton: { backgroundColor: '#F59E0B', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12, gap: 8 },
  approveText: { color: '#fff', fontWeight: 'bold' },
  photoProof: { width: '100%', height: 200, borderRadius: 12, marginTop: 12 }
});
"""

# 8. TasksScreen - Image Picker Logic
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView, Switch } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { Ionicons } from '@expo/vector-icons';
import { api, getMembers } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';
import { useAuth } from '../context/AuthContext';
import * as ImagePicker from 'expo-image-picker';

const PREDEFINED_TASKS = [
  { title: 'Bajar la basura', points: 5, icon: 'trash-outline' },
  { title: 'Hacer la cama', points: 5, icon: 'bed-outline' },
  { title: 'Limpieza a fondo', points: 100, icon: 'sparkles-outline' },
];

export default function TasksScreen() {
  const { user } = useAuth();
  const { tasks, fetchTasks, completeTask } = useTaskStore();
  const [members, setMembers] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('10');
  const [freq, setFreq] = useState('ONCE');
  const [assignType, setAssignType] = useState('MANUAL');
  const [fixedUser, setFixedUser] = useState<string | null>(null);
  const [requiresPhoto, setRequiresPhoto] = useState(false);
  const [startDateStr, setStartDateStr] = useState(new Date().toISOString().split('T')[0]);
  const [endDateStr, setEndDateStr] = useState('');

  useEffect(() => { fetchTasks(); getMembers().then(setMembers).catch(() => {}); }, []);

  const handleComplete = async (item: any) => {
    if (item.template.requires_photo) {
      let result = await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5 });
      if (!result.canceled && result.assets[0].uri) {
        // En un entorno real se subiría a S3/Firebase Storage. Para MVP, mandamos la URI base64 o local.
        await completeTask(item.id, result.assets[0].uri);
      }
    } else {
      setShowConfetti(false);
      await completeTask(item.id);
      setShowConfetti(true);
    }
  };

  const handleCreate = async () => {
    if (!title) return;
    try {
      await api.post('/tasks', {
        title, points, frequency: freq, start_date: startDateStr, end_date: endDateStr || null,
        assignment_type: assignType, fixed_user_id: fixedUser, requires_photo: requiresPhoto
      });
      setModalVisible(false); fetchTasks();
    } catch (e: any) { alert('Error: ' + e.message); }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Planificación</Text>
      </View>
      <FlatList data={tasks} keyExtractor={t => t.id} renderItem={({item}) => <TaskCard item={item} currentUserId={user?.uid as string} onComplete={() => handleComplete(item)} />} contentContainerStyle={styles.list} />
      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}><Ionicons name="add" size={32} color="#fff" /></TouchableOpacity>
      {showConfetti && <ConfettiCannon count={100} origin={{x: -10, y: 0}} fallSpeed={2000} />}

      <Modal visible={modalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.modalTitle}>Nueva Tarea</Text>
              
              <TextInput style={styles.input} placeholder="¿Qué hay que hacer?" value={title} onChangeText={setTitle} />
              
              <View style={{flexDirection: 'row', gap: 16, marginTop:16}}>
                <View style={{flex: 1}}><Text style={styles.label}>Puntos:</Text><TextInput style={styles.input} keyboardType="numeric" value={points} onChangeText={setPoints} /></View>
                <View style={{flex: 1}}><Text style={styles.label}>Frecuencia:</Text><TextInput style={styles.input} value={freq} onChangeText={setFreq} placeholder="ONCE" /></View>
              </View>

              <View style={{flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, backgroundColor: '#FCE7F3', padding: 16, borderRadius: 12}}>
                 <Text style={{fontWeight: 'bold', color: '#DB2777'}}>📸 Requiere Verificación por Foto</Text>
                 <Switch value={requiresPhoto} onValueChange={setRequiresPhoto} trackColor={{true: '#DB2777'}} />
              </View>

              <Text style={styles.label}>Asignación:</Text>
              <View style={styles.freqContainer}>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'MANUAL' && styles.freqBtnActive]} onPress={() => setAssignType('MANUAL')}><Text style={[styles.freqText, assignType === 'MANUAL' && styles.freqTextActive]}>Pizarra Común</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'RANDOM' && styles.freqBtnActive]} onPress={() => setAssignType('RANDOM')}><Text style={[styles.freqText, assignType === 'RANDOM' && styles.freqTextActive]}>Aleatorio</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'FIXED' && styles.freqBtnActive]} onPress={() => { setAssignType('FIXED'); setFixedUser(members[0]?.id); }}><Text style={[styles.freqText, assignType === 'FIXED' && styles.freqTextActive]}>Fija</Text></TouchableOpacity>
              </View>

              {assignType === 'FIXED' && (
                <View style={[styles.freqContainer, {marginTop: 8}]}>
                  {members.map(m => (<TouchableOpacity key={m.id} style={[styles.freqBtn, fixedUser === m.id && styles.freqBtnActive]} onPress={() => setFixedUser(m.id)}><Text style={[styles.freqText, fixedUser === m.id && styles.freqTextActive]}>👤 {m.name}</Text></TouchableOpacity>))}
                </View>
              )}

              <View style={styles.modalButtons}>
                <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}><Text>Cancelar</Text></TouchableOpacity>
                <TouchableOpacity onPress={handleCreate} style={styles.saveButton}><Text style={{color: '#fff', fontWeight:'bold'}}>Guardar</Text></TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', borderBottomWidth:1, borderColor:'#E5E7EB' },
  headerTitle: { fontSize: 28, fontWeight: '900', color: '#111827' },
  list: { padding: 16 },
  fab: { position: 'absolute', bottom: 24, right: 24, width: 64, height: 64, borderRadius: 32, backgroundColor: '#4F46E5', justifyContent: 'center', alignItems: 'center' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', padding: 24, borderTopLeftRadius: 32, borderTopRightRadius: 32, maxHeight: '85%' },
  modalTitle: { fontSize: 24, fontWeight: '800', marginBottom: 20 },
  label: { fontSize: 16, fontWeight: 'bold', color: '#374151', marginBottom: 10, marginTop: 16 },
  freqContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  freqBtn: { paddingHorizontal: 16, paddingVertical: 10, borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 12 },
  freqBtnActive: { backgroundColor: '#EEF2FF', borderColor: '#4F46E5' },
  freqText: { color: '#6B7280', fontWeight: '600' },
  freqTextActive: { color: '#4F46E5' },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, fontSize: 16 },
  modalButtons: { flexDirection: 'row', justifyContent: 'flex-end', gap: 16, marginTop: 32 },
  cancelButton: { padding: 16 },
  saveButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 12, minWidth:120, alignItems:'center' }
});
"""

# 9. ProfileScreen - Transfers, Streak, MVP
files["mobile/src/screens/ProfileScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, TextInput, ScrollView, Platform, Modal } from 'react-native';
import { api, getMembers, kickMember, transferPoints } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { triggerWowEffect } from '../utils/SoundHaptics';

export default function ProfileScreen() {
  const { logout } = useAuth();
  const navigation = useNavigation<any>();
  const [settings, setSettings] = useState<any>({ penalty_enabled: true, penalty_percentage: 50, name: 'Piso', id: '', role: 'MEMBER' });
  const [members, setMembers] = useState<any[]>([]);
  const [myStats, setMyStats] = useState<any>({});
  const [transferModal, setTransferModal] = useState(false);
  const [selectedMember, setSelectedMember] = useState<any>(null);
  const [transferAmount, setTransferAmount] = useState('');

  const fetchData = () => {
    api.get('/group/settings').then(res => setSettings(res.data)).catch(()=>{});
    getMembers().then(res => setMembers(res)).catch(()=>{});
    api.get('/users/dashboard').then(res => setMyStats(res.data)).catch(()=>{});
  };

  useEffect(() => { fetchData(); }, []);

  const openTransfer = (member: any) => {
    setSelectedMember(member); setTransferAmount(''); setTransferModal(true);
  };

  const handleTransfer = async () => {
    if (!transferAmount || isNaN(Number(transferAmount))) return;
    try {
      await transferPoints(selectedMember.id, transferAmount);
      await triggerWowEffect();
      setTransferModal(false);
      fetchData();
    } catch(e: any) { alert(e.response?.data?.error || 'Error'); }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}><Ionicons name="arrow-back" size={24} style={{marginRight: 16}}/></TouchableOpacity>
        <Text style={styles.headerTitle}>Mi Perfil</Text>
      </View>
      
      <ScrollView contentContainerStyle={styles.content}>
        
        <View style={{flexDirection: 'row', justifyContent: 'space-around', backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 24}}>
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 24}}>🔥</Text>
              <Text style={{fontSize: 20, fontWeight: 'bold'}}>{myStats.streak || 0}</Text>
              <Text style={{fontSize: 12, color: '#6B7280'}}>Racha (días)</Text>
           </View>
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 24}}>{myStats.is_mvp ? '👑' : '⭐'}</Text>
              <Text style={{fontSize: 20, fontWeight: 'bold'}}>{myStats.totalPoints || 0}</Text>
              <Text style={{fontSize: 12, color: '#6B7280'}}>Puntos</Text>
           </View>
        </View>

        <Text style={styles.sectionTitle}>Compañeros (Mercado Negro)</Text>
        <View style={styles.card}>
          {members.map((m, i) => (
            <TouchableOpacity key={m.id} style={[styles.memberRow, i < members.length-1 && {borderBottomWidth: 1, borderColor:'#F3F4F6'}]} onPress={() => openTransfer(m)}>
              <View>
                <Text style={styles.memberName}>{m.name} {m.is_mvp ? '👑 (MVP Semanal)' : ''}</Text>
                <Text style={styles.memberPoints}>{m.points} pts acumulados</Text>
              </View>
              <View style={{flexDirection: 'row', alignItems: 'center'}}>
                 <Text style={{color: '#4F46E5', fontWeight: 'bold', marginRight: 8}}>Sobornar</Text>
                 <Ionicons name="cash-outline" size={20} color="#4F46E5" />
              </View>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity onPress={logout} style={styles.logoutButton}>
          <Text style={styles.logoutText}>Cerrar Sesión</Text>
        </TouchableOpacity>
      </ScrollView>

      <Modal visible={transferModal} animationType="slide" transparent={true}>
        <View style={{flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', padding: 20}}>
           <View style={{backgroundColor: '#fff', padding: 24, borderRadius: 24}}>
              <Text style={{fontSize: 20, fontWeight: 'bold', marginBottom: 16}}>Transferir puntos a {selectedMember?.name}</Text>
              <TextInput style={{backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, fontSize: 18, marginBottom: 24}} placeholder="Ej. 50" keyboardType="numeric" value={transferAmount} onChangeText={setTransferAmount} />
              <View style={{flexDirection: 'row', justifyContent: 'flex-end', gap: 16}}>
                 <TouchableOpacity onPress={() => setTransferModal(false)} style={{padding: 16}}><Text>Cancelar</Text></TouchableOpacity>
                 <TouchableOpacity onPress={handleTransfer} style={{backgroundColor: '#4F46E5', padding: 16, borderRadius: 12}}><Text style={{color:'#fff', fontWeight:'bold'}}>Transferir</Text></TouchableOpacity>
              </View>
           </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', flexDirection: 'row', alignItems: 'center' },
  headerTitle: { fontSize: 24, fontWeight: '800' },
  content: { padding: 16 },
  sectionTitle: { fontSize: 14, fontWeight: 'bold', color: '#6B7280', marginBottom: 12, marginLeft: 4, textTransform: 'uppercase' },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 16 },
  memberRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12 },
  memberName: { fontSize: 16, fontWeight: 'bold' },
  memberPoints: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  logoutButton: { backgroundColor: '#FEE2E2', padding: 16, borderRadius: 16, alignItems: 'center', marginTop: 24, marginBottom: 40 },
  logoutText: { color: '#EF4444', fontWeight: 'bold', fontSize: 16 }
});
"""

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Mega feature expansion injected locally.")
