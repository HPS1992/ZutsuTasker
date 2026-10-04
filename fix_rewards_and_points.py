import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update RewardRoutes to fix Foreign Key constraint
files["backend/src/routes/rewardRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    const rewards = await prisma.reward.findMany({ where: { group_id: member.group_id } });
    res.json(rewards);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const { title, cost_points } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member || member.role !== 'ADMIN') return res.status(403).json({ error: 'Solo los administradores pueden añadir recompensas' });

    const reward = await prisma.reward.create({
      data: {
        group_id: member.group_id,
        title,
        cost_points: parseInt(cost_points)
      }
    });
    res.json(reward);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.delete('/:id', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member || member.role !== 'ADMIN') return res.status(403).json({ error: 'Solo los administradores pueden borrar recompensas' });
    
    const reward = await prisma.reward.findUnique({ where: { id: req.params.id } });
    if (!reward || reward.group_id !== member.group_id) return res.status(403).json({ error: 'Acceso denegado' });

    // FIX: Eliminar el historial de canjes asociados primero para no violar la Foreign Key
    await prisma.$transaction([
      prisma.rewardRedemption.deleteMany({ where: { reward_id: req.params.id } }),
      prisma.reward.delete({ where: { id: req.params.id } })
    ]);
    
    res.json({ success: true });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/:id/redeem', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const { id } = req.params;
    
    const reward = await prisma.reward.findUnique({ where: { id } });
    if (!reward) return res.status(404).json({ error: 'Reward not found' });

    const member = await prisma.groupMember.findUnique({
      where: { user_id_group_id: { user_id: user.id, group_id: reward.group_id } }
    });

    if (!member || member.total_points < reward.cost_points) {
      return res.status(400).json({ error: 'Not enough points' });
    }

    await prisma.$transaction([
      prisma.groupMember.update({
        where: { user_id_group_id: { user_id: user.id, group_id: reward.group_id } },
        data: { total_points: member.total_points - reward.cost_points }
      }),
      prisma.rewardRedemption.create({
        data: { reward_id: reward.id, user_id: user.id }
      }),
      prisma.pointsLog.create({
        data: { user_id: user.id, group_id: reward.group_id, amount: -reward.cost_points, reason: 'REWARD_CLAIM' }
      })
    ]);

    res.json({ success: true, message: 'Recompensa canjeada' });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
"""

# 2. Update TasksScreen (Expand Predefined list and styling)
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { Ionicons } from '@expo/vector-icons';
import { api, getMembers } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';

const PREDEFINED_TASKS = [
  { title: 'Bajar la basura', points: 5, icon: 'trash-outline' },
  { title: 'Hacer la cama', points: 5, icon: 'bed-outline' },
  { title: 'Fregar los platos', points: 15, icon: 'water-outline' },
  { title: 'Poner/Tender lavadora', points: 20, icon: 'shirt-outline' },
  { title: 'Cocinar comida/cena', points: 25, icon: 'restaurant-outline' },
  { title: 'Barrer y fregar', points: 30, icon: 'home-outline' },
  { title: 'Hacer la compra', points: 40, icon: 'cart-outline' },
  { title: 'Limpiar el baño', points: 50, icon: 'sparkles-outline' },
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
  const [points, setPoints] = useState('10');
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

    try {
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
    } catch (e: any) {
      alert('Error al crear tarea: ' + (e.response?.data?.error || e.message));
    }
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
              
              <Text style={styles.label}>Catálogo Rápido (Puntos por defecto):</Text>
              <View style={styles.chipsContainer}>
                {PREDEFINED_TASKS.map((t, i) => (
                  <TouchableOpacity key={i} style={[styles.chip, title === t.title && styles.chipActive]} onPress={() => selectPredefined(t)}>
                    <Ionicons name={t.icon as any} size={16} color={title === t.title ? '#fff' : '#4B5563'} style={{marginRight: 6}} />
                    <Text style={[styles.chipText, title === t.title && styles.chipTextActive]}>{t.title} ({t.points})</Text>
                  </TouchableOpacity>
                ))}
                <TouchableOpacity style={[styles.chip, isCustom && styles.chipActive]} onPress={() => { setIsCustom(true); setTitle(''); setPoints('10'); }}>
                  <Text style={[styles.chipText, isCustom && styles.chipTextActive]}>+ Personalizada...</Text>
                </TouchableOpacity>
              </View>

              {isCustom && (
                <TextInput style={styles.input} placeholder="Escribe tu tarea..." value={title} onChangeText={setTitle} />
              )}
              
              <Text style={styles.label}>Puntos de recompensa (Modificable):</Text>
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
  chip: { paddingHorizontal: 16, paddingVertical: 10, backgroundColor: '#F3F4F6', borderRadius: 20, flexDirection: 'row', alignItems: 'center' },
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
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Marketplace foreign key fix applied and predefined tasks expanded with fair points.")
