import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

if "is_on_vacation" not in schema:
    schema = schema.replace(
        "role         String   @default(\"MEMBER\")",
        "role         String   @default(\"MEMBER\")\n  is_on_vacation Boolean  @default(false)"
    )
    schema = schema.replace(
        "frequency      String         @default(\"ONCE\")",
        "frequency      String         @default(\"ONCE\")\n  start_date     DateTime       @default(now())\n  end_date       DateTime?"
    )
files["backend/prisma/schema.prisma"] = schema

# 2. Update Backend Task Routes (Accept start/end dates)
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
    const { title, description, points, frequency, assignment_type, fixed_user_id, start_date, end_date } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let initialAssignee = null;
    if (assignment_type === 'RANDOM') {
      const allMembers = await prisma.groupMember.findMany({ 
          where: { group_id: member.group_id, is_on_vacation: false }, 
          orderBy: { total_points: 'asc' } 
      });
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
        fixed_user_id: assignment_type === 'FIXED' ? fixed_user_id : null,
        start_date: start_date ? new Date(start_date) : new Date(),
        end_date: end_date ? new Date(end_date) : null
      }
    });

    const instance = await prisma.taskInstance.create({
      data: {
        template_id: template.id,
        group_id: member.group_id,
        due_date: template.start_date,
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

# 3. Update taskService for Vacation & End Date Logic
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
    let penaltyApplied = false;

    // Solo penalizar si el assigned_to original no estaba de vacaciones
    if (isOverdue && task.group.penalty_enabled && task.assigned_to) {
        const originalAssignee = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
        if (originalAssignee && !originalAssignee.is_on_vacation) {
            points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
            penaltyApplied = true;
        }
    }

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, assigned_to: userId } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } }, data: { total_points: member.total_points + points } }),
      prisma.pointsLog.create({ data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETION' } })
    ]);

    await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);
    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien completó: ${task.template.title}`, userId);
    return { success: true, message: `Tarea completada, +${points} puntos` };
  },

  async stealTask(taskId: string, thiefId: string) {
    const task = await prisma.taskInstance.findUnique({
      where: { id: taskId }, include: { template: true, group: true }
    });
    if (!task || task.status === 'COMPLETED') throw new Error('Task unavailable');
    if (!task.assigned_to || task.assigned_to === thiefId) throw new Error('No puedes robar esta tarea');

    const victimMember = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
    if (victimMember?.is_on_vacation) throw new Error('No puedes robarle tareas a alguien en modo vacaciones');

    const now = new Date();
    const timeDiff = now.getTime() - task.due_date.getTime();
    const daysOverdue = timeDiff / (1000 * 3600 * 24);

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
      
      // Chequeo de Fecha de Fin
      if (template.end_date && nextDate > new Date(template.end_date)) {
        return; // Excedió la fecha de finalización, muere la tarea recurrente
      }

      let nextAssignee = null;
      if (template.assignment_type === 'RANDOM') {
        const members = await prisma.groupMember.findMany({ 
            where: { group_id: groupId, is_on_vacation: false }, 
            orderBy: { total_points: 'asc' } 
        });
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

# 4. Update Profile Route to toggle vacation
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
      role: member ? member.role : null,
      is_on_vacation: member ? member.is_on_vacation : false
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

router.post('/vacation', requireAuth, async (req, res) => {
  try {
    const { is_on_vacation } = req.body;
    await prisma.groupMember.updateMany({
      where: { user_id: req.user.id },
      data: { is_on_vacation }
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

# 5. Update ProfileScreen UI
profile_path = os.path.join(base_dir, "mobile/src/screens/ProfileScreen.tsx")
with open(profile_path, "r") as f:
    profile_content = f.read()

if "const [vacationMode, setVacationMode] = useState(false);" not in profile_content:
    profile_content = profile_content.replace(
      "const [reminderTime, setReminderTime] = useState('10:00');",
      "const [reminderTime, setReminderTime] = useState('10:00');\n  const [vacationMode, setVacationMode] = useState(false);"
    )
    profile_content = profile_content.replace(
      "api.get('/users/dashboard').then(res => setReminderTime(res.data.reminder_time)).catch(console.error);",
      "api.get('/users/dashboard').then(res => { setReminderTime(res.data.reminder_time); setVacationMode(res.data.is_on_vacation); }).catch(console.error);"
    )
    profile_content = profile_content.replace(
      "</View>\n          <View style={[styles.row, {marginTop: 16}]}>",
      """</View>
          <View style={[styles.row, {marginTop: 16}]}>
            <View>
               <Text style={styles.settingText}>🌴 Modo Vacaciones</Text>
               <Text style={styles.helperText}>Pausa tareas y penalizaciones</Text>
            </View>
            <Switch value={vacationMode} onValueChange={(val) => { setVacationMode(val); api.post('/users/vacation', { is_on_vacation: val }); }} trackColor={{true: '#F59E0B'}} />
          </View>
          <View style={[styles.row, {marginTop: 16}]}>"""
    )
files["mobile/src/screens/ProfileScreen.tsx"] = profile_content

# 6. Update TasksScreen UI (Start Date / End Date Input)
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView } from 'react-native';
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
  const { tasks, fetchTasks, completeTask } = useTaskStore();
  const [members, setMembers] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('10');
  const [freq, setFreq] = useState('ONCE');
  const [assignType, setAssignType] = useState('MANUAL');
  const [fixedUser, setFixedUser] = useState<string | null>(null);
  
  // Novedad: Fechas
  const [startDateStr, setStartDateStr] = useState(new Date().toISOString().split('T')[0]);
  const [endDateStr, setEndDateStr] = useState('');

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
    try {
      await api.post('/tasks', {
        title, points, frequency: freq, 
        start_date: startDateStr, 
        end_date: endDateStr || null,
        assignment_type: assignType, 
        fixed_user_id: fixedUser
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
              
              <View style={{flexDirection: 'row', gap: 16}}>
                <View style={{flex: 1}}>
                  <Text style={styles.label}>Puntos:</Text>
                  <TextInput style={styles.input} keyboardType="numeric" value={points} onChangeText={setPoints} />
                </View>
                <View style={{flex: 1}}>
                  <Text style={styles.label}>Frecuencia:</Text>
                  <TextInput style={styles.input} value={freq} onChangeText={setFreq} placeholder="ONCE/DAILY/WEEKLY" />
                </View>
              </View>
              
              <Text style={styles.label}>Calendario (YYYY-MM-DD):</Text>
              <View style={{flexDirection: 'row', gap: 16}}>
                <View style={{flex: 1}}>
                  <TextInput style={styles.input} value={startDateStr} onChangeText={setStartDateStr} placeholder="Inicio" />
                </View>
                <View style={{flex: 1}}>
                  <TextInput style={styles.input} value={endDateStr} onChangeText={setEndDateStr} placeholder="Fin (Opcional)" />
                </View>
              </View>

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

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Vacation mode and Start/End dates implemented.")
