import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r") as f:
    schema = f.read()

if "status      String   @default(\"PENDING\")" not in schema:
    schema = schema.replace(
        "redeemed_at DateTime @default(now())",
        "redeemed_at DateTime @default(now())\n  status      String   @default(\"PENDING\")"
    )
    with open(schema_path, "w") as f:
        f.write(schema)

# 2. Update backend routes
files["backend/src/routes/rewardRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';
import { notificationService } from '../services/notificationService';

const router = Router();
const prisma = new PrismaClient();

router.get('/', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });
    const rewards = await prisma.reward.findMany({ where: { group_id: member.group_id } });
    res.json(rewards);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const { title, cost_points } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member || member.role !== 'ADMIN') return res.status(403).json({ error: 'Solo los administradores' });
    const reward = await prisma.reward.create({ data: { group_id: member.group_id, title, cost_points: parseInt(cost_points) } });
    res.json(reward);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.delete('/:id', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member || member.role !== 'ADMIN') return res.status(403).json({ error: 'Denegado' });
    await prisma.$transaction([
      prisma.rewardRedemption.deleteMany({ where: { reward_id: req.params.id } }),
      prisma.reward.delete({ where: { id: req.params.id } })
    ]);
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/redeem', requireAuth, async (req, res) => {
  try {
    const reward = await prisma.reward.findUnique({ where: { id: req.params.id } });
    if (!reward) return res.status(404).json({ error: 'Reward not found' });
    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: req.user.id, group_id: reward.group_id } } });
    if (!member || member.total_points < reward.cost_points) return res.status(400).json({ error: 'Puntos insuficientes' });

    await prisma.$transaction([
      prisma.groupMember.update({ where: { id: member.id }, data: { total_points: member.total_points - reward.cost_points } }),
      prisma.rewardRedemption.create({ data: { reward_id: reward.id, user_id: req.user.id, status: 'PENDING' } }),
      prisma.pointsLog.create({ data: { user_id: req.user.id, group_id: reward.group_id, amount: -reward.cost_points, reason: 'REWARD_CLAIM' } })
    ]);
    
    await notificationService.notifyGroup(reward.group_id, '🎁 Recompensa Canjeada', `${req.user.name} ha canjeado: ${reward.title}. ¡Pendiente de disfrutar!`, req.user.id);
    res.json({ success: true, message: 'Recompensa canjeada y pendiente de disfrutar' });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get('/redemptions', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.json([]);
    const redemptions = await prisma.rewardRedemption.findMany({
      where: { reward: { group_id: member.group_id }, status: 'PENDING' },
      include: { reward: true, user: true },
      orderBy: { redeemed_at: 'desc' }
    });
    res.json(redemptions);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/redemptions/:id/complete', requireAuth, async (req, res) => {
  try {
    const redemption = await prisma.rewardRedemption.findUnique({ where: { id: req.params.id }, include: { reward: true } });
    if (!redemption) return res.status(404).json({ error: 'Not found' });
    if (redemption.user_id !== req.user.id) return res.status(403).json({ error: 'Solo puedes dar por completado tu propio canje' });
    
    await prisma.rewardRedemption.update({ where: { id: req.params.id }, data: { status: 'COMPLETED' } });
    await notificationService.notifyGroup(redemption.reward.group_id, '✅ Recompensa Disfrutada', `${req.user.name} por fin ha disfrutado: ${redemption.reward.title}`, req.user.id);
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

# 3. Update api.ts
api_path = os.path.join(base_dir, "mobile/src/services/api.ts")
with open(api_path, "r") as f:
    api_content = f.read()

if "getRedemptions" not in api_content:
    api_content += "\nexport const getRedemptions = async () => (await api.get('/rewards/redemptions')).data;\n"
    api_content += "export const completeRedemption = async (id: string) => (await api.post(`/rewards/redemptions/${id}/complete`)).data;\n"
    with open(api_path, "w") as f:
        f.write(api_content)

# 4. Update MarketScreen.tsx
files["mobile/src/screens/MarketScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, ActivityIndicator, Modal, TextInput, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getRewards, createReward, deleteReward, redeemReward, getRedemptions, completeRedemption, api } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';
import { useAuth } from '../context/AuthContext';
import { triggerWowEffect } from '../utils/SoundHaptics';

export default function MarketScreen() {
  const { user } = useAuth();
  const [rewards, setRewards] = useState<any[]>([]);
  const [redemptions, setRedemptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [title, setTitle] = useState('');
  const [cost, setCost] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  const currentUserId = user?.id || user?.uid;

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      getRewards(), 
      getRedemptions(),
      api.get('/users/dashboard').then(res => setIsAdmin(res.data.role === 'ADMIN')).catch(()=>{})
    ])
    .then(([rew, red]) => { setRewards(rew); setRedemptions(red); })
    .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreate = async () => {
    if (!title || !cost) return;
    try {
      await createReward({ title, cost_points: parseInt(cost) });
      setModalVisible(false);
      setTitle(''); setCost('');
      fetchData();
    } catch(e: any) { alert(e.response?.data?.error || 'Error al crear'); }
  };

  const handleRedeem = async (id: string) => {
    try {
      await redeemReward(id);
      await triggerWowEffect();
      setShowConfetti(true);
      fetchData();
      setTimeout(() => setShowConfetti(false), 3000);
    } catch(e: any) {
      alert(e.response?.data?.error || 'No tienes puntos suficientes');
    }
  };

  const handleCompleteRedemption = async (id: string) => {
    try {
      await completeRedemption(id);
      await triggerWowEffect();
      fetchData();
    } catch(e: any) { alert(e.response?.data?.error || 'Error'); }
  };

  const handleDelete = async (id: string) => {
    const confirmDelete = async () => {
      try { await deleteReward(id); fetchData(); } 
      catch(e: any) { alert(e.response?.data?.error || 'No se pudo borrar'); }
    };

    if (Platform.OS === 'web') {
      if (window.confirm('¿Estás seguro de borrar esta recompensa?')) await confirmDelete();
    } else {
      Alert.alert('Borrar', '¿Seguro?', [ { text: 'Cancelar', style: 'cancel' }, { text: 'Borrar', style: 'destructive', onPress: confirmDelete } ]);
    }
  };

  const renderReward = ({ item }: any) => (
    <View style={styles.card}>
      <View style={{flex: 1}}>
         <Text style={styles.title}>{item.title}</Text>
         <Text style={styles.points}><Ionicons name="star" size={14} color="#F59E0B" /> {item.cost_points} pts</Text>
      </View>
      <View style={{flexDirection: 'row', gap: 8, alignItems: 'center'}}>
        <TouchableOpacity style={styles.redeemButton} onPress={() => handleRedeem(item.id)}>
          <Text style={styles.redeemText}>Canjear</Text>
        </TouchableOpacity>
        {isAdmin && (
          <TouchableOpacity onPress={() => handleDelete(item.id)} style={{padding: 8, backgroundColor:'#FEE2E2', borderRadius:8}}>
            <Ionicons name="trash-outline" size={20} color="#EF4444" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Marketplace</Text>
        <Text style={styles.subtitle}>Gasta tus puntos ganados</Text>
      </View>

      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#4F46E5"/> : (
        <FlatList
          ListHeaderComponent={
            redemptions.length > 0 ? (
              <View style={styles.pendingSection}>
                <Text style={styles.sectionTitle}>⏳ Tickets Pendientes</Text>
                {redemptions.map(r => (
                  <View key={r.id} style={styles.pendingCard}>
                    <View style={{flex: 1}}>
                      <Text style={styles.pendingTitle}>{r.reward.title}</Text>
                      <Text style={styles.pendingUser}>De: {r.user.id === currentUserId ? 'Ti' : r.user.name}</Text>
                    </View>
                    {r.user.id === currentUserId ? (
                      <TouchableOpacity style={styles.completeBtn} onPress={() => handleCompleteRedemption(r.id)}>
                        <Text style={styles.completeBtnText}>¡Disfrutada!</Text>
                      </TouchableOpacity>
                    ) : (
                      <Text style={styles.waitingText}>Esperando...</Text>
                    )}
                  </View>
                ))}
              </View>
            ) : null
          }
          data={rewards}
          renderItem={renderReward}
          keyExtractor={i => i.id}
          contentContainerStyle={styles.list}
        />
      )}

      {isAdmin && (
        <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
          <Ionicons name="add" size={32} color="#fff" />
        </TouchableOpacity>
      )}

      {showConfetti && <ConfettiCannon count={100} origin={{x: -10, y: 0}} fallSpeed={2000} />}

      <Modal visible={modalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Nueva Recompensa</Text>
            
            <Text style={styles.label}>Nombre del premio:</Text>
            <TextInput style={styles.input} placeholder="Ej: Pizza el viernes" value={title} onChangeText={setTitle} />
            
            <Text style={styles.label}>Coste en puntos:</Text>
            <TextInput style={styles.input} keyboardType="numeric" value={cost} onChangeText={setCost} />

            <View style={styles.modalButtons}>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}><Text>Cancelar</Text></TouchableOpacity>
              <TouchableOpacity onPress={handleCreate} style={styles.saveButton}><Text style={{color: '#fff', fontWeight:'bold'}}>Guardar</Text></TouchableOpacity>
            </View>
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
  subtitle: { color: '#6B7280', marginTop: 8, fontSize:16 },
  list: { padding: 16 },
  pendingSection: { marginBottom: 24 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#374151', marginBottom: 12, textTransform: 'uppercase' },
  pendingCard: { backgroundColor: '#FEF3C7', padding: 16, borderRadius: 16, marginBottom: 8, flexDirection: 'row', alignItems: 'center' },
  pendingTitle: { fontSize: 16, fontWeight: 'bold', color: '#92400E' },
  pendingUser: { fontSize: 14, color: '#B45309', marginTop: 4 },
  waitingText: { color: '#B45309', fontStyle: 'italic', fontSize: 12 },
  completeBtn: { backgroundColor: '#D97706', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  completeBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 12 },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'center' },
  title: { fontSize: 18, fontWeight: 'bold', color: '#111827', marginBottom: 4 },
  points: { fontSize: 14, color: '#F59E0B', fontWeight: '700' },
  redeemButton: { backgroundColor: '#4F46E5', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 12 },
  redeemText: { color: '#fff', fontWeight: 'bold' },
  fab: { position: 'absolute', bottom: 24, right: 24, width: 64, height: 64, borderRadius: 32, backgroundColor: '#10B981', justifyContent: 'center', alignItems: 'center' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', padding: 24, borderTopLeftRadius: 32, borderTopRightRadius: 32 },
  modalTitle: { fontSize: 24, fontWeight: '800', marginBottom: 20 },
  label: { fontSize: 16, fontWeight: 'bold', color: '#374151', marginBottom: 10, marginTop: 16 },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, fontSize: 16 },
  modalButtons: { flexDirection: 'row', justifyContent: 'flex-end', gap: 16, marginTop: 32 },
  cancelButton: { padding: 16 },
  saveButton: { backgroundColor: '#10B981', padding: 16, borderRadius: 12, minWidth:120, alignItems:'center' }
});
"""

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Pending redemption logic implemented.")
