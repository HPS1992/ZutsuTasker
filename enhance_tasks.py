import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema for Frequency
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

if "frequency" not in schema:
    schema = schema.replace(
        "points        Int",
        "points        Int\n  frequency     String    @default(\"ONCE\") // ONCE, DAILY, WEEKLY, MONTHLY"
    )
files["backend/prisma/schema.prisma"] = schema

# 2. Update Backend Task Routes (Delete & Create with Frequency)
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
    const { title, description, points, due_date, frequency } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    const template = await prisma.taskTemplate.create({
      data: { group_id: member.group_id, title, description: description || '', points: parseInt(points), frequency: frequency || 'ONCE' }
    });

    const instance = await prisma.taskInstance.create({
      data: {
        template_id: template.id,
        group_id: member.group_id,
        due_date: new Date(due_date || new Date()),
        status: 'PENDING'
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
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });
    
    // Verificar que la tarea pertenece a su grupo
    const task = await prisma.taskInstance.findUnique({ where: { id } });
    if (!task || task.group_id !== member.group_id) return res.status(403).json({ error: 'Acceso denegado' });

    await prisma.taskInstance.delete({ where: { id } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

# 3. Update taskService (Auto-respawn recurring tasks)
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

    await prisma.$transaction([
      prisma.taskInstance.update({
        where: { id: taskId },
        data: { status: 'COMPLETED', completed_at: now, assigned_user_id: userId }
      }),
      prisma.groupMember.update({
        where: { user_id_group_id: { user_id: userId, group_id: task.group_id } },
        data: { total_points: member.total_points + points }
      }),
      prisma.pointsLog.create({
        data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETION' }
      })
    ]);

    // Lógica de recurrencia
    const freq = task.template.frequency;
    if (freq && freq !== 'ONCE') {
      const nextDate = new Date(now);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);
      
      await prisma.taskInstance.create({
        data: {
          template_id: task.template.id,
          group_id: task.group_id,
          due_date: nextDate,
          status: 'PENDING'
        }
      });
    }

    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien acaba de completar: ${task.template.title}`, userId);

    return { success: true, message: `Tarea completada, +${points} puntos` };
  }
};
"""

# 4. Update Frontend store (delete task)
files["mobile/src/store/useTaskStore.ts"] = """import { create } from 'zustand';
import { getTasks, completeTask as completeTaskApi, api } from '../services/api';

interface TaskState {
  tasks: any[];
  loading: boolean;
  fetchTasks: () => Promise<void>;
  completeTask: (id: string) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  loading: false,
  fetchTasks: async () => {
    set({ loading: true });
    try {
      const data = await getTasks();
      set({ tasks: data });
    } finally {
      set({ loading: false });
    }
  },
  completeTask: async (id: string) => {
    await completeTaskApi(id);
    const updated = await getTasks();
    set({ tasks: updated });
  },
  deleteTask: async (id: string) => {
    await api.delete(`/tasks/${id}`);
    const updated = await getTasks();
    set({ tasks: updated });
  }
}));
"""

# 5. Update TaskCard Component (Add Trash Icon)
files["mobile/src/components/TaskCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTaskStore } from '../store/useTaskStore';

export const TaskCard = ({ item, onComplete }: { item: any, onComplete: () => void }) => {
  const isCompleted = item.status === 'COMPLETED';
  const isOverdue = new Date() > new Date(item.due_date);
  const { deleteTask } = useTaskStore();

  return (
    <View style={[styles.card, isCompleted && styles.cardCompleted]}>
      <View style={styles.content}>
        <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'}}>
           <View style={{flex: 1}}>
              <Text style={[styles.title, isCompleted && styles.textCompleted]}>{item.template.title}</Text>
              <Text style={styles.points}>
                <Ionicons name="star" size={14} color="#F59E0B" /> {item.template.points} pts 
                {item.template.frequency !== 'ONCE' ? ` • ${item.template.frequency === 'DAILY' ? 'Diaria' : item.template.frequency === 'WEEKLY' ? 'Semanal' : 'Mensual'}` : ''}
              </Text>
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
  points: { fontSize: 14, color: '#F59E0B', fontWeight: '700', marginBottom: 16 },
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 },
  date: { fontSize: 13, color: '#6B7280', fontWeight: '500' },
  dateOverdue: { color: '#EF4444', fontWeight: '700' },
  completeButton: { backgroundColor: '#10B981', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12, gap: 8 },
  completeText: { color: '#fff', fontWeight: 'bold' }
});
"""

# 6. Update TasksScreen (Predefined list + Frequency Picker)
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../services/api';
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
  const { tasks, fetchTasks, completeTask, loading } = useTaskStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  
  // Form state
  const [isCustom, setIsCustom] = useState(false);
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('20');
  const [freq, setFreq] = useState('ONCE');

  useEffect(() => { fetchTasks(); }, []);

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
      due_date: due.toISOString()
    });
    setModalVisible(false);
    setTitle('');
    setIsCustom(false);
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
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, fontSize: 16 },
  modalButtons: { flexDirection: 'row', justifyContent: 'flex-end', gap: 16, marginTop: 32 },
  cancelButton: { padding: 16 },
  saveButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 12, minWidth:120, alignItems:'center' }
});
"""

# 7. Update ProfileScreen (Add Share/Invite button correctly)
files["mobile/src/screens/ProfileScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, Alert, TextInput, ScrollView, Share } from 'react-native';
import { api, getMembers, kickMember } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';

export default function ProfileScreen() {
  const { logout } = useAuth();
  const navigation = useNavigation<any>();
  const [settings, setSettings] = useState<any>({ penalty_enabled: true, penalty_percentage: 50, name: 'Piso', id: '', role: 'MEMBER' });
  const [pushEnabled, setPushEnabled] = useState(true);
  const [members, setMembers] = useState<any[]>([]);

  const fetchData = () => {
    api.get('/group/settings').then(res => setSettings(res.data)).catch(console.error);
    getMembers().then(res => setMembers(res)).catch(console.error);
  };

  useEffect(() => { fetchData(); }, []);

  const saveGroupSettings = async (updates: any) => {
    if (settings.role !== 'ADMIN') return Alert.alert('Error', 'Solo los administradores pueden cambiar los ajustes.');
    const newSet = { ...settings, ...updates };
    setSettings(newSet);
    try { await api.post('/group/settings', newSet); } 
    catch (e) { Alert.alert('Error', 'No se pudo guardar la configuración'); }
  };

  const handleShareCode = async () => {
    try {
      await Share.share({
        message: `¡Únete a mi hogar "${settings.name}" en Zutsu Tasker!\n\nCódigo de invitación: ${settings.id}\n\nDescarga la app y equibremos las tareas.`,
      });
    } catch (error) {
      Alert.alert('Error', 'No se pudo compartir');
    }
  };

  const handleKick = (userId: string, name: string) => {
    Alert.alert('Expulsar', `¿Seguro que quieres expulsar a ${name}?`, [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Expulsar', style: 'destructive', onPress: async () => {
          try { await kickMember(userId); fetchData(); } 
          catch(e) { Alert.alert('Error', 'No se pudo expulsar'); }
      }}
    ]);
  };

  const isAdmin = settings.role === 'ADMIN';

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}><Ionicons name="arrow-back" size={24} color="#111827" style={{marginRight: 16}}/></TouchableOpacity>
        <Text style={styles.headerTitle}>Gestión del Hogar</Text>
      </View>
      
      <ScrollView contentContainerStyle={styles.content}>
        
        <Text style={styles.sectionTitle}>Código de Invitación</Text>
        <TouchableOpacity style={styles.inviteCard} onPress={handleShareCode}>
          <Text style={styles.inviteText}>ID: {settings.id}</Text>
          <View style={styles.shareBadge}>
             <Ionicons name="share-social-outline" size={20} color="#fff" />
             <Text style={styles.shareText}>Invitar</Text>
          </View>
        </TouchableOpacity>

        <Text style={styles.sectionTitle}>Miembros del Grupo</Text>
        <View style={styles.card}>
          {members.map((m, i) => (
            <View key={m.id} style={[styles.memberRow, i < members.length-1 && {borderBottomWidth: 1, borderColor:'#F3F4F6'}]}>
              <View>
                <Text style={styles.memberName}>{m.name} {m.role === 'ADMIN' ? '👑' : ''}</Text>
                <Text style={styles.memberPoints}>{m.points} pts acumulados</Text>
              </View>
              {isAdmin && m.role !== 'ADMIN' && (
                <TouchableOpacity onPress={() => handleKick(m.id, m.name)}>
                  <Ionicons name="trash-outline" size={20} color="#EF4444" />
                </TouchableOpacity>
              )}
            </View>
          ))}
        </View>

        <Text style={styles.sectionTitle}>Ajustes Generales</Text>
        <View style={styles.card}>
          <Text style={styles.settingText}>Nombre del Grupo</Text>
          <TextInput 
            style={[styles.input, !isAdmin && {backgroundColor:'#E5E7EB', color:'#9CA3AF'}]} 
            value={settings.name} 
            editable={isAdmin}
            onChangeText={t => setSettings({...settings, name: t})} 
            onBlur={() => saveGroupSettings({ name: settings.name })}
          />
        </View>

        <TouchableOpacity onPress={logout} style={styles.logoutButton}>
          <Ionicons name="log-out-outline" size={20} color="#EF4444" style={{marginRight:8}}/>
          <Text style={styles.logoutText}>Cerrar Sesión</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', borderBottomWidth:1, borderColor:'#E5E7EB', flexDirection: 'row', alignItems: 'center' },
  headerTitle: { fontSize: 24, fontWeight: '800', color: '#111827' },
  content: { padding: 16 },
  sectionTitle: { fontSize: 14, fontWeight: 'bold', color: '#6B7280', marginBottom: 12, marginLeft: 4, textTransform: 'uppercase', marginTop: 12 },
  inviteCard: { backgroundColor: '#4F46E5', padding: 20, borderRadius: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  inviteText: { fontSize: 16, fontWeight: 'bold', color: '#fff', flex: 1 },
  shareBadge: { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 20, flexDirection: 'row', alignItems: 'center', gap: 6 },
  shareText: { color: '#fff', fontWeight: 'bold' },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 16 },
  memberRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12 },
  memberName: { fontSize: 16, fontWeight: 'bold', color: '#111827' },
  memberPoints: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  settingText: { fontSize: 16, fontWeight: '600', color: '#374151' },
  helperText: { fontSize: 13, color: '#6B7280', marginTop: 12, lineHeight: 20 },
  input: { backgroundColor: '#F9FAFB', padding: 12, borderRadius: 8, marginTop: 12, borderWidth: 1, borderColor: '#E5E7EB', fontSize: 16 },
  logoutButton: { backgroundColor: '#FEE2E2', padding: 16, borderRadius: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 24, marginBottom: 40 },
  logoutText: { color: '#EF4444', fontWeight: 'bold', fontSize: 16 }
});
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Tasks recurrences and share invite finished.")
