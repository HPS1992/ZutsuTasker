import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

if "assignment_type" not in schema:
    schema = schema.replace(
        "push_token       String?",
        "push_token       String?\n  reminder_time    String             @default(\"10:00\")"
    )
    schema = schema.replace(
        "is_rotational  Boolean        @default(false)\n  rotation_index Int            @default(0)",
        "assignment_type String        @default(\"MANUAL\") // RANDOM, MANUAL, FIXED\n  fixed_user_id   String?"
    )
files["backend/prisma/schema.prisma"] = schema

# 2. Update Backend Routes
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

    const tasks = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id },
      include: { template: true, assigned_user: true },
      orderBy: { due_date: 'asc' }
    });
    res.json(tasks.map(t => ({...t, assigned_to: t.assigned_user})));
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const { title, description, points, due_date, frequency, assignment_type, fixed_user_id } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let initialAssignee = null;

    if (assignment_type === 'RANDOM') {
      const allMembers = await prisma.groupMember.findMany({ where: { group_id: member.group_id }, orderBy: { total_points: 'asc' } });
      if (allMembers.length > 0) initialAssignee = allMembers[0].user_id;
    } else if (assignment_type === 'FIXED' && fixed_user_id) {
      initialAssignee = fixed_user_id;
    }

    const template = await prisma.taskTemplate.create({
      data: { 
        group_id: member.group_id, 
        title, 
        description: description || '', 
        points: parseInt(points) || 10, 
        frequency: frequency || 'ONCE',
        assignment_type: assignment_type || 'MANUAL',
        fixed_user_id: assignment_type === 'FIXED' ? fixed_user_id : null
      }
    });

    const instance = await prisma.taskInstance.create({
      data: {
        template_id: template.id,
        group_id: member.group_id,
        due_date: new Date(due_date || new Date()),
        status: 'PENDING',
        assigned_to: initialAssignee
      }
    });

    res.json({ template, instance });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/complete', requireAuth, async (req, res) => {
  try {
    const result = await taskService.completeTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/claim', requireAuth, async (req, res) => {
  try {
    const task = await prisma.taskInstance.update({
      where: { id: req.params.id },
      data: { assigned_to: req.user.id }
    });
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
    const task = await prisma.taskInstance.findUnique({ where: { id: req.params.id } });
    if (task) await prisma.taskInstance.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

# 3. Update taskService for Mechanics (Steal, Random Respawn)
files["backend/src/services/taskService.ts"] = """import { PrismaClient } from '@prisma/client';
import { notificationService } from './notificationService';

const prisma = new PrismaClient();

export const taskService = {
  async completeTask(taskId: string, userId: string) {
    const task = await prisma.taskInstance.findUnique({
      where: { id: taskId },
      include: { template: true, group: true }
    });
    if (!task || task.status === 'COMPLETED') throw new Error('Task unavailable');

    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } } });
    if (!member) throw new Error('Not part of group');

    const now = new Date();
    const isOverdue = now > task.due_date;
    
    let points = task.template.points;
    if (isOverdue && task.group.penalty_enabled) {
      points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
    }

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, assigned_to: userId } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } }, data: { total_points: member.total_points + points } }),
      prisma.pointsLog.create({ data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETION' } })
    ]);

    await this.spawnNextInstance(task.template, task.group_id, now);
    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien completó: ${task.template.title}`, userId);
    return { success: true, message: `Tarea completada, +${points} puntos` };
  },

  async stealTask(taskId: string, thiefId: string) {
    const task = await prisma.taskInstance.findUnique({
      where: { id: taskId }, include: { template: true, group: true }
    });
    if (!task || task.status === 'COMPLETED') throw new Error('Task unavailable');
    if (!task.assigned_to || task.assigned_to === thiefId) throw new Error('No puedes robar esta tarea');

    const now = new Date();
    const timeDiff = now.getTime() - task.due_date.getTime();
    const daysOverdue = timeDiff / (1000 * 3600 * 24);

    if (daysOverdue < 0 || daysOverdue > 2) throw new Error('Solo puedes robar tareas vencidas hace menos de 2 días');

    const basePoints = task.template.points;
    const stolenReward = Math.floor(basePoints * 1.5);
    const stolenPenalty = Math.floor(basePoints * 0.5);

    const thiefMember = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: thiefId, group_id: task.group_id } } });
    const victimMember = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
    if (!thiefMember || !victimMember) throw new Error('Group error');

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, assigned_to: thiefId } }),
      
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: thiefId, group_id: task.group_id } }, data: { total_points: thiefMember.total_points + stolenReward } }),
      prisma.pointsLog.create({ data: { user_id: thiefId, group_id: task.group_id, amount: stolenReward, reason: 'TASK_STOLEN_REWARD' } }),

      prisma.groupMember.update({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } }, data: { total_points: victimMember.total_points - stolenPenalty } }),
      prisma.pointsLog.create({ data: { user_id: task.assigned_to, group_id: task.group_id, amount: -stolenPenalty, reason: 'TASK_STOLEN_PENALTY' } })
    ]);

    await this.spawnNextInstance(task.template, task.group_id, now);
    await notificationService.notifyGroup(task.group_id, '🥷 ¡Tarea robada!', `Alguien ha robado: ${task.template.title}`, thiefId);
    return { success: true, message: `¡Tarea robada! +${stolenReward} pts para ti, -${stolenPenalty} pts para la víctima.` };
  },

  async spawnNextInstance(template: any, groupId: string, now: Date) {
    const freq = template.frequency;
    if (freq && freq !== 'ONCE') {
      const nextDate = new Date(now);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);
      
      let nextAssignee = null;
      if (template.assignment_type === 'RANDOM') {
        const members = await prisma.groupMember.findMany({ where: { group_id: groupId }, orderBy: { total_points: 'asc' } });
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

# 4. Update Profile Route & API
files["backend/src/routes/userRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/dashboard', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({
      where: { user_id: user.id },
      include: { group: true }
    });

    res.json({
      id: user.id,
      name: user.name,
      reminder_time: user.reminder_time,
      totalPoints: member ? member.total_points : 0,
      streak: member ? member.streak_days : 0,
      groupName: member ? member.group.name : null,
      groupId: member ? member.group.id : null,
      role: member ? member.role : null
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/settings', requireAuth, async (req, res) => {
  try {
    const { reminder_time } = req.body;
    await prisma.user.update({
      where: { id: req.user.id },
      data: { reminder_time }
    });
    res.json({ success: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/push-token', requireAuth, async (req, res) => {
  try {
    const { token } = req.body;
    await prisma.user.update({
      where: { id: req.user.id },
      data: { push_token: token }
    });
    res.json({ success: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
"""

files["mobile/src/services/api.ts"] = """import axios from 'axios';
import { Platform } from 'react-native';

const API_URL = Platform.OS === 'web' && typeof window !== 'undefined' 
  ? `${window.location.origin}/api` 
  : 'http://localhost:3000/api';

export const api = axios.create({ baseURL: API_URL, headers: { 'Content-Type': 'application/json' } });

export const getTasks = async () => (await api.get(`/tasks`)).data;
export const createTask = async (data: any) => (await api.post(`/tasks`, data)).data;
export const completeTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/complete`)).data;
export const claimTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/claim`)).data;
export const stealTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/steal`)).data;

export const getRewards = async () => (await api.get(`/rewards`)).data;
export const createReward = async (data: any) => (await api.post(`/rewards`, data)).data;
export const deleteReward = async (id: string) => (await api.delete(`/rewards/${id}`)).data;
export const redeemReward = async (id: string) => (await api.post(`/rewards/${id}/redeem`)).data;

export const getEquityStats = async () => (await api.get(`/stats/equity`)).data;

export const createGroup = async (name: string) => (await api.post('/group/create', { name })).data;
export const joinGroup = async (groupId: string) => (await api.post('/group/join', { groupId })).data;
export const getMembers = async () => (await api.get('/group/members')).data;
export const kickMember = async (userId: string) => (await api.delete(`/group/members/${userId}`)).data;
"""

# 5. Update TaskCard UI (Claim & Steal)
files["mobile/src/components/TaskCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTaskStore } from '../store/useTaskStore';

export const TaskCard = ({ item, currentUserId, onComplete }: { item: any, currentUserId: string, onComplete: () => void }) => {
  const isCompleted = item.status === 'COMPLETED';
  const now = new Date();
  const dueDate = new Date(item.due_date);
  const isOverdue = now > dueDate;
  const daysOverdue = (now.getTime() - dueDate.getTime()) / (1000 * 3600 * 24);
  
  const { deleteTask, claimTask, stealTask } = useTaskStore();
  
  const assigneeName = item.assigned_to ? item.assigned_to.name : null;
  const isMine = item.assigned_to?.id === currentUserId;
  const isManual = item.template.assignment_type === 'MANUAL';
  
  const canSteal = !isCompleted && isOverdue && daysOverdue <= 2 && assigneeName && !isMine;
  const canClaim = !isCompleted && !assigneeName && isManual;

  return (
    <View style={[styles.card, isCompleted && styles.cardCompleted]}>
      <View style={styles.content}>
        <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'}}>
           <View style={{flex: 1}}>
              <Text style={[styles.title, isCompleted && styles.textCompleted]}>{item.template.title}</Text>
              
              <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap'}}>
                 <Text style={styles.points}><Ionicons name="star" size={14} color="#F59E0B" /> {item.template.points} pts</Text>
                 
                 {item.template.frequency !== 'ONCE' && (
                   <View style={styles.badge}>
                     <Ionicons name="repeat" size={12} color="#4F46E5" />
                     <Text style={styles.badgeText}>{item.template.frequency === 'DAILY' ? 'Diaria' : item.template.frequency === 'WEEKLY' ? 'Semanal' : 'Mensual'}</Text>
                   </View>
                 )}
                 
                 <View style={[styles.badge, {backgroundColor: '#FEF3C7'}]}>
                   <Ionicons name={assigneeName ? 'person' : 'people'} size={12} color="#B45309" />
                   <Text style={[styles.badgeText, {color: '#B45309'}]}>
                      {assigneeName ? (isMine ? 'Mía' : assigneeName) : 'Pizarra Común'}
                   </Text>
                 </View>
                 
                 {item.template.assignment_type === 'RANDOM' && (
                   <View style={[styles.badge, {backgroundColor: '#D1FAE5'}]}>
                     <Ionicons name="shuffle" size={12} color="#059669" />
                     <Text style={[styles.badgeText, {color: '#059669'}]}>Aleatoria</Text>
                   </View>
                 )}
              </View>
           </View>
           {!isCompleted && (
              <TouchableOpacity onPress={() => deleteTask(item.id)} style={{padding: 8, backgroundColor:'#FEE2E2', borderRadius:8}}>
                 <Ionicons name="trash-outline" size={20} color="#EF4444" />
              </TouchableOpacity>
           )}
        </View>

        <View style={styles.footer}>
          <Text style={[styles.date, isOverdue && !isCompleted && styles.dateOverdue]}>
            <Ionicons name="time-outline" size={14} /> 
            {' '}{dueDate.toLocaleDateString('es-ES')}
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

            {!isCompleted && (!assigneeName || isMine || (!canSteal && !canClaim)) && (
              <TouchableOpacity style={[styles.completeButton, (!isMine && assigneeName) && {opacity: 0.5}]} onPress={onComplete} disabled={!isMine && !!assigneeName}>
                <Text style={styles.completeText}>Completar</Text>
                <Ionicons name="checkmark-circle" size={20} color="#fff" />
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
  stealText: { color: '#fff', fontWeight: 'bold' }
});
"""

# 6. Update TasksScreen (New Modal Form & currentUserId)
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView, Alert } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { Ionicons } from '@expo/vector-icons';
import { api, getMembers } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';
import { useAuth } from '../context/AuthContext';

const PREDEFINED_TASKS = [
  { title: 'Bajar la basura', points: 5, icon: 'trash-outline' },
  { title: 'Hacer la cama', points: 5, icon: 'bed-outline' },
  { title: 'Fregar los platos', points: 15, icon: 'water-outline' },
  { title: 'Poner la lavadora', points: 20, icon: 'shirt-outline' },
  { title: 'Limpiar el baño', points: 50, icon: 'sparkles-outline' },
];

export default function TasksScreen() {
  const { user } = useAuth();
  const { tasks, fetchTasks, completeTask, loading } = useTaskStore();
  const [members, setMembers] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  
  // Form state
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('10');
  const [freq, setFreq] = useState('ONCE');
  const [assignType, setAssignType] = useState('MANUAL');
  const [fixedUser, setFixedUser] = useState<string | null>(null);

  useEffect(() => { 
    fetchTasks();
    getMembers().then(setMembers).catch(() => {});
  }, []);

  const handleComplete = async (id: string) => {
    setShowConfetti(false);
    await completeTask(id);
    setShowConfetti(true);
  };

  const handleCreate = async () => {
    if (!title) return;
    const due = new Date();
    if (freq === 'DAILY') due.setDate(due.getDate() + 1);
    else if (freq === 'WEEKLY') due.setDate(due.getDate() + 7);
    else if (freq === 'MONTHLY') due.setMonth(due.getMonth() + 1);

    try {
      await api.post('/tasks', {
        title, points, frequency: freq, due_date: due.toISOString(),
        assignment_type: assignType, fixed_user_id: fixedUser
      });
      setModalVisible(false);
      fetchTasks();
    } catch (e: any) { alert('Error: ' + e.message); }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Planificación</Text>
      </View>
      
      <FlatList 
        data={tasks} keyExtractor={t => t.id}
        renderItem={({item}) => <TaskCard item={item} currentUserId={user?.uid as string} onComplete={() => handleComplete(item.id)} />}
        contentContainerStyle={styles.list}
      />

      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
        <Ionicons name="add" size={32} color="#fff" />
      </TouchableOpacity>
      {showConfetti && <ConfettiCannon count={100} origin={{x: -10, y: 0}} fallSpeed={2000} />}

      <Modal visible={modalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.modalTitle}>Nueva Tarea</Text>
              
              <Text style={styles.label}>Tarea:</Text>
              <TextInput style={styles.input} placeholder="¿Qué hay que hacer?" value={title} onChangeText={setTitle} />
              
              <Text style={styles.label}>Puntos:</Text>
              <TextInput style={styles.input} keyboardType="numeric" value={points} onChangeText={setPoints} />

              <Text style={styles.label}>Método de Asignación:</Text>
              <View style={styles.freqContainer}>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'MANUAL' && styles.freqBtnActive]} onPress={() => setAssignType('MANUAL')}>
                  <Text style={[styles.freqText, assignType === 'MANUAL' && styles.freqTextActive]}>Pizarra Común (Manual)</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'RANDOM' && styles.freqBtnActive]} onPress={() => setAssignType('RANDOM')}>
                  <Text style={[styles.freqText, assignType === 'RANDOM' && styles.freqTextActive]}>Aleatorio (Equitativo)</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'FIXED' && styles.freqBtnActive]} onPress={() => { setAssignType('FIXED'); setFixedUser(members[0]?.id); }}>
                  <Text style={[styles.freqText, assignType === 'FIXED' && styles.freqTextActive]}>Fija (Miembro)</Text>
                </TouchableOpacity>
              </View>

              {assignType === 'FIXED' && (
                <View style={[styles.freqContainer, {marginTop: 8}]}>
                  {members.map(m => (
                    <TouchableOpacity key={m.id} style={[styles.freqBtn, fixedUser === m.id && styles.freqBtnActive]} onPress={() => setFixedUser(m.id)}>
                      <Text style={[styles.freqText, fixedUser === m.id && styles.freqTextActive]}>👤 {m.name}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}

              <Text style={styles.label}>Frecuencia:</Text>
              <View style={styles.freqContainer}>
                {['ONCE', 'DAILY', 'WEEKLY', 'MONTHLY'].map(f => (
                  <TouchableOpacity key={f} style={[styles.freqBtn, freq === f && styles.freqBtnActive]} onPress={() => setFreq(f)}>
                    <Text style={[styles.freqText, freq === f && styles.freqTextActive]}>{f === 'ONCE' ? 'Puntual' : f}</Text>
                  </TouchableOpacity>
                ))}
              </View>

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

# 7. Update Task Store
files["mobile/src/store/useTaskStore.ts"] = """import { create } from 'zustand';
import { getTasks, completeTask as completeTaskApi, claimTask as claimTaskApi, stealTask as stealTaskApi, api } from '../services/api';
import { Alert } from 'react-native';

interface TaskState {
  tasks: any[];
  loading: boolean;
  fetchTasks: () => Promise<void>;
  completeTask: (id: string) => Promise<void>;
  claimTask: (id: string) => Promise<void>;
  stealTask: (id: string) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  loading: false,
  fetchTasks: async () => {
    set({ loading: true });
    try { const data = await getTasks(); set({ tasks: data }); } 
    finally { set({ loading: false }); }
  },
  completeTask: async (id: string) => {
    await completeTaskApi(id);
    const updated = await getTasks(); set({ tasks: updated });
  },
  claimTask: async (id: string) => {
    await claimTaskApi(id);
    const updated = await getTasks(); set({ tasks: updated });
  },
  stealTask: async (id: string) => {
    try {
      const res = await stealTaskApi(id);
      Alert.alert('¡Robo completado!', res.message);
      const updated = await getTasks(); set({ tasks: updated });
    } catch(e: any) { Alert.alert('Error al robar', e.response?.data?.error || e.message); }
  },
  deleteTask: async (id: string) => {
    await api.delete(`/tasks/${id}`);
    const updated = await getTasks(); set({ tasks: updated });
  }
}));
"""

# 8. Update ProfileScreen (Add Reminder Time)
profile_path = os.path.join(base_dir, "mobile/src/screens/ProfileScreen.tsx")
with open(profile_path, "r") as f:
    profile_content = f.read()

# Modify settings state
profile_content = profile_content.replace(
  "const [pushEnabled, setPushEnabled] = useState(true);",
  "const [pushEnabled, setPushEnabled] = useState(true);\n  const [reminderTime, setReminderTime] = useState('10:00');"
)
# Fetch reminder_time
profile_content = profile_content.replace(
  "api.get('/group/settings').then(res => setSettings(res.data)).catch(console.error);",
  "api.get('/group/settings').then(res => setSettings(res.data)).catch(console.error);\n    api.get('/users/dashboard').then(res => setReminderTime(res.data.reminder_time)).catch(console.error);"
)
# Save reminder_time
profile_content = profile_content.replace(
  "const isAdmin = settings.role === 'ADMIN';",
  "const isAdmin = settings.role === 'ADMIN';\n  const saveUserReminder = () => { api.post('/users/settings', { reminder_time: reminderTime }).catch(()=>{}); };"
)
# Add input UI
profile_content = profile_content.replace(
  "<Switch value={pushEnabled} onValueChange={setPushEnabled} trackColor={{true: '#10B981'}} />\n          </View>\n        </View>",
  """<Switch value={pushEnabled} onValueChange={setPushEnabled} trackColor={{true: '#10B981'}} />
          </View>
          <View style={[styles.row, {marginTop: 16}]}>
            <Text style={styles.settingText}>Hora del recordatorio (HH:MM)</Text>
            <TextInput style={[styles.input, {marginTop:0, width: 80, textAlign:'center'}]} value={reminderTime} onChangeText={setReminderTime} onBlur={saveUserReminder} placeholder="10:00" />
          </View>
        </View>"""
)

files["mobile/src/screens/ProfileScreen.tsx"] = profile_content


for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Game mechanics (Random, Manual, Steal, Reminders) successfully injected.")
