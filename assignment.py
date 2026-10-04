import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

if "is_rotational" not in schema:
    schema = schema.replace(
        "frequency     String    @default(\"ONCE\") // ONCE, DAILY, WEEKLY, MONTHLY",
        "frequency     String    @default(\"ONCE\")\n  is_rotational Boolean   @default(false)\n  rotation_index Int      @default(0)"
    )
files["backend/prisma/schema.prisma"] = schema


# 2. Update Backend Task Routes
files["backend/src/routes/taskRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { taskService } from '../services/taskService';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    const tasks = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id },
      include: { template: true, assigned_to: true },
      orderBy: { due_date: 'asc' }
    });
    res.json(tasks);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const { title, description, points, due_date, frequency, assignment_method } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let is_rotational = assignment_method === 'ROTATIONAL';
    let initialAssignee = null;
    let rotationIndex = 0;

    if (is_rotational) {
      // Asignar al primero del grupo por defecto
      const allMembers = await prisma.groupMember.findMany({ where: { group_id: member.group_id }, orderBy: { joined_at: 'asc' } });
      if (allMembers.length > 0) initialAssignee = allMembers[0].user_id;
    } else if (assignment_method !== 'ANY') {
      // Specific user id
      initialAssignee = assignment_method;
    }

    const template = await prisma.taskTemplate.create({
      data: { 
        group_id: member.group_id, 
        title, 
        description: description || '', 
        points: parseInt(points), 
        frequency: frequency || 'ONCE',
        is_rotational,
        rotation_index: rotationIndex
      }
    });

    const instance = await prisma.taskInstance.create({
      data: {
        template_id: template.id,
        group_id: member.group_id,
        due_date: new Date(due_date || new Date()),
        status: 'PENDING',
        assigned_user_id: initialAssignee
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

router.delete('/:id', requireAuth, async (req, res) => {
  try {
    const { id } = req.params;
    const task = await prisma.taskInstance.findUnique({ where: { id } });
    if (!task) return res.status(404).json({ error: 'Not found' });
    await prisma.taskInstance.delete({ where: { id } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

# 3. Update taskService for Rotation
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

    const member = await prisma.groupMember.findUnique({
      where: { user_id_group_id: { user_id: userId, group_id: task.group_id } }
    });
    if (!member) throw new Error('Not part of group');

    const now = new Date();
    const isOverdue = now > task.due_date;
    
    let points = task.template.points;
    if (isOverdue && task.group.penalty_enabled) {
      points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
    }

    // Quién la ha completado gana los puntos, incluso si no era el asignado inicialmente
    await prisma.$transaction([
      prisma.taskInstance.update({
        where: { id: taskId },
        data: { status: 'COMPLETED', completed_at: now, assigned_user_id: userId } // Override assigned with who completed it
      }),
      prisma.groupMember.update({
        where: { user_id_group_id: { user_id: userId, group_id: task.group_id } },
        data: { total_points: member.total_points + points }
      }),
      prisma.pointsLog.create({
        data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETION' }
      })
    ]);

    // Lógica de recurrencia y rotación
    const freq = task.template.frequency;
    if (freq && freq !== 'ONCE') {
      const nextDate = new Date(now);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);
      
      let nextAssignee = task.assigned_user_id; // Por defecto hereda a quien la completó o a nadie
      
      if (task.template.is_rotational) {
        const members = await prisma.groupMember.findMany({ 
            where: { group_id: task.group_id },
            orderBy: { joined_at: 'asc' } 
        });
        const nextIndex = (task.template.rotation_index + 1) % members.length;
        
        await prisma.taskTemplate.update({
            where: { id: task.template.id },
            data: { rotation_index: nextIndex }
        });
        nextAssignee = members[nextIndex].user_id;
      }

      await prisma.taskInstance.create({
        data: {
          template_id: task.template.id,
          group_id: task.group_id,
          due_date: nextDate,
          status: 'PENDING',
          assigned_user_id: nextAssignee
        }
      });
    }

    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien acaba de completar: ${task.template.title}`, userId);

    return { success: true, message: `Tarea completada, +${points} puntos` };
  }
};
"""

# 4. Update TaskCard to show Assignment
files["mobile/src/components/TaskCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTaskStore } from '../store/useTaskStore';

export const TaskCard = ({ item, onComplete }: { item: any, onComplete: () => void }) => {
  const isCompleted = item.status === 'COMPLETED';
  const isOverdue = new Date() > new Date(item.due_date);
  const { deleteTask } = useTaskStore();

  const assigneeName = item.assigned_to ? item.assigned_to.name : null;
  const isRotational = item.template.is_rotational;

  return (
    <View style={[styles.card, isCompleted && styles.cardCompleted]}>
      <View style={styles.content}>
        <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'}}>
           <View style={{flex: 1}}>
              <Text style={[styles.title, isCompleted && styles.textCompleted]}>{item.template.title}</Text>
              
              <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 12, gap: 12}}>
                 <Text style={styles.points}>
                   <Ionicons name="star" size={14} color="#F59E0B" /> {item.template.points} pts
                 </Text>
                 {item.template.frequency !== 'ONCE' && (
                   <View style={styles.badge}>
                     <Ionicons name="repeat" size={12} color="#4F46E5" />
                     <Text style={styles.badgeText}>{item.template.frequency === 'DAILY' ? 'Diaria' : item.template.frequency === 'WEEKLY' ? 'Semanal' : 'Mensual'}</Text>
                   </View>
                 )}
                 {(assigneeName || isRotational) && (
                   <View style={[styles.badge, {backgroundColor: '#FEF3C7'}]}>
                     <Ionicons name={isRotational ? 'sync' : 'person'} size={12} color="#B45309" />
                     <Text style={[styles.badgeText, {color: '#B45309'}]}>
                        {isRotational && !isCompleted ? `Turno de ${assigneeName || 'Todos'}` : assigneeName}
                     </Text>
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
            {' '}{new Date(item.due_date).toLocaleDateString('es-ES')}
          </Text>
          
          {!isCompleted && (
            <TouchableOpacity style={styles.completeButton} onPress={onComplete}>
              <Text style={styles.completeText}>Completar</Text>
              <Ionicons name="checkmark-circle" size={20} color="#fff" />
            </TouchableOpacity>
          )}
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
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 },
  date: { fontSize: 13, color: '#6B7280', fontWeight: '500' },
  dateOverdue: { color: '#EF4444', fontWeight: '700' },
  completeButton: { backgroundColor: '#10B981', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12, gap: 8 },
  completeText: { color: '#fff', fontWeight: 'bold' }
});
"""

# 5. Update TasksScreen (Add Assignment UI)
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { Ionicons } from '@expo/vector-icons';
import { api, getMembers } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';

const PREDEFINED_TASKS = [
  { title: 'Fregar los platos', points: 20 },
  { title: 'Bajar la basura', points: 10 },
  { title: 'Poner la lavadora', points: 30 },
  { title: 'Limpiar el baño', points: 50 },
  { title: 'Hacer la compra', points: 40 },
];

const FREQUENCIES = [
  { id: 'ONCE', label: 'Una vez' },
  { id: 'DAILY', label: 'Diaria' },
  { id: 'WEEKLY', label: 'Semanal' },
  { id: 'MONTHLY', label: 'Mensual' },
];

export default function TasksScreen() {
  const { tasks, fetchTasks, completeTask } = useTaskStore();
  const [members, setMembers] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  
  // Form state
  const [isCustom, setIsCustom] = useState(false);
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('20');
  const [freq, setFreq] = useState('ONCE');
  const [assignMethod, setAssignMethod] = useState('ANY');

  useEffect(() => { 
    fetchTasks();
    getMembers().then(setMembers).catch(() => {});
  }, []);

  const handleComplete = async (id: string) => {
    setShowConfetti(false);
    await completeTask(id);
    setShowConfetti(true);
  };

  const selectPredefined = (item: any) => {
    setIsCustom(false);
    setTitle(item.title);
    setPoints(item.points.toString());
  };

  const handleCreate = async () => {
    if (!title) return;
    const due = new Date();
    if (freq === 'DAILY') due.setDate(due.getDate() + 1);
    else if (freq === 'WEEKLY') due.setDate(due.getDate() + 7);
    else if (freq === 'MONTHLY') due.setMonth(due.getMonth() + 1);

    await api.post('/tasks', {
      title,
      points,
      frequency: freq,
      due_date: due.toISOString(),
      assignment_method: assignMethod
    });
    
    setModalVisible(false);
    setTitle('');
    setIsCustom(false);
    setAssignMethod('ANY');
    fetchTasks();
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Tareas del Hogar</Text>
      </View>
      
      <FlatList 
        data={tasks} 
        keyExtractor={t => t.id}
        renderItem={({item}) => <TaskCard item={item} onComplete={() => handleComplete(item.id)} />}
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
              <Text style={styles.modalTitle}>✨ Nueva Tarea</Text>
              
              <Text style={styles.label}>Rápidas:</Text>
              <View style={styles.chipsContainer}>
                {PREDEFINED_TASKS.map((t, i) => (
                  <TouchableOpacity key={i} style={[styles.chip, title === t.title && styles.chipActive]} onPress={() => selectPredefined(t)}>
                    <Text style={[styles.chipText, title === t.title && styles.chipTextActive]}>{t.title}</Text>
                  </TouchableOpacity>
                ))}
                <TouchableOpacity style={[styles.chip, isCustom && styles.chipActive]} onPress={() => { setIsCustom(true); setTitle(''); setPoints('10'); }}>
                  <Text style={[styles.chipText, isCustom && styles.chipTextActive]}>Personalizada...</Text>
                </TouchableOpacity>
              </View>

              {isCustom && (
                <TextInput style={styles.input} placeholder="Escribe tu tarea..." value={title} onChangeText={setTitle} />
              )}
              
              <Text style={styles.label}>Puntos de recompensa:</Text>
              <TextInput style={styles.input} keyboardType="numeric" value={points} onChangeText={setPoints} />

              <Text style={styles.label}>Asignación:</Text>
              <View style={styles.freqContainer}>
                <TouchableOpacity style={[styles.freqBtn, assignMethod === 'ANY' && styles.freqBtnActive]} onPress={() => setAssignMethod('ANY')}>
                  <Text style={[styles.freqText, assignMethod === 'ANY' && styles.freqTextActive]}>Libre</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignMethod === 'ROTATIONAL' && styles.freqBtnActive]} onPress={() => setAssignMethod('ROTATIONAL')}>
                  <Text style={[styles.freqText, assignMethod === 'ROTATIONAL' && styles.freqTextActive]}>🔄 Rotativa</Text>
                </TouchableOpacity>
                {members.map(m => (
                  <TouchableOpacity key={m.id} style={[styles.freqBtn, assignMethod === m.id && styles.freqBtnActive]} onPress={() => setAssignMethod(m.id)}>
                    <Text style={[styles.freqText, assignMethod === m.id && styles.freqTextActive]}>👤 {m.name}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.label}>Frecuencia:</Text>
              <View style={styles.freqContainer}>
                {FREQUENCIES.map(f => (
                  <TouchableOpacity key={f.id} style={[styles.freqBtn, freq === f.id && styles.freqBtnActive]} onPress={() => setFreq(f.id)}>
                    <Text style={[styles.freqText, freq === f.id && styles.freqTextActive]}>{f.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <View style={styles.modalButtons}>
                <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}><Text>Cancelar</Text></TouchableOpacity>
                <TouchableOpacity onPress={handleCreate} style={styles.saveButton}><Text style={{color: '#fff', fontWeight:'bold'}}>Añadir Tarea</Text></TouchableOpacity>
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
  fab: { position: 'absolute', bottom: 24, right: 24, width: 64, height: 64, borderRadius: 32, backgroundColor: '#4F46E5', justifyContent: 'center', alignItems: 'center', shadowColor: '#4F46E5', shadowOpacity: 0.4, shadowRadius: 10, elevation: 5 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', padding: 24, borderTopLeftRadius: 32, borderTopRightRadius: 32, maxHeight: '85%' },
  modalTitle: { fontSize: 24, fontWeight: '800', marginBottom: 20, color:'#111827' },
  label: { fontSize: 16, fontWeight: 'bold', color: '#374151', marginBottom: 10, marginTop: 16 },
  chipsContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingHorizontal: 16, paddingVertical: 10, backgroundColor: '#F3F4F6', borderRadius: 20 },
  chipActive: { backgroundColor: '#4F46E5' },
  chipText: { color: '#4B5563', fontWeight: '500' },
  chipTextActive: { color: '#fff' },
  freqContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  freqBtn: { paddingHorizontal: 16, paddingVertical: 10, borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 12 },
  freqBtnActive: { backgroundColor: '#EEF2FF', borderColor: '#4F46E5' },
  freqText: { color: '#6B7280', fontWeight: '600' },
  freqTextActive: { color: '#4F46E5' },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, fontSize: 16, marginTop: 8 },
  modalButtons: { flexDirection: 'row', justifyContent: 'flex-end', gap: 16, marginTop: 32 },
  cancelButton: { padding: 16 },
  saveButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 12, minWidth:120, alignItems:'center' }
});
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Métodos de asignación y rotación implementados con éxito.")
