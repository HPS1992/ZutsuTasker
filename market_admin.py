import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Añadir el Rol al Dashboard
user_routes_path = os.path.join(base_dir, "backend/src/routes/userRoutes.ts")
with open(user_routes_path, "r") as f:
    user_routes = f.read()
    
if "role: member ? member.role : null" not in user_routes:
    user_routes = user_routes.replace(
        "groupId: member ? member.group.id : null",
        "groupId: member ? member.group.id : null,\n      role: member ? member.role : null"
    )
files["backend/src/routes/userRoutes.ts"] = user_routes


# 2. Rutas del Marketplace (Protección ADMIN y Delete)
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
    
    // Check ownership of reward
    const reward = await prisma.reward.findUnique({ where: { id: req.params.id } });
    if (!reward || reward.group_id !== member.group_id) return res.status(403).json({ error: 'Acceso denegado' });

    await prisma.reward.delete({ where: { id: req.params.id } });
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

# 3. Actualizar el Frontend API
files["mobile/src/services/api.ts"] = """import axios from 'axios';
import { Platform } from 'react-native';

const API_URL = Platform.OS === 'web' && typeof window !== 'undefined' 
  ? `${window.location.origin}/api` 
  : 'http://localhost:3000/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const getTasks = async () => (await api.get(`/tasks`)).data;
export const createTask = async (data: any) => (await api.post(`/tasks`, data)).data;
export const completeTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/complete`)).data;

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

# 4. Actualizar la Pantalla del Market (Controles Admin y Borrado)
files["mobile/src/screens/MarketScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Alert, ActivityIndicator, Modal, TextInput } from 'react-native';
import { getRewards, redeemReward, createReward, deleteReward, api } from '../services/api';
import { Ionicons } from '@expo/vector-icons';

export default function MarketScreen() {
  const [rewards, setRewards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [myPoints, setMyPoints] = useState(0);
  const [isAdmin, setIsAdmin] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  
  const [title, setTitle] = useState('');
  const [cost, setCost] = useState('100');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [rewRes, dashRes] = await Promise.all([getRewards(), api.get('/users/dashboard')]);
      setRewards(rewRes);
      setMyPoints(dashRes.data.totalPoints);
      setIsAdmin(dashRes.data.role === 'ADMIN');
    } catch (error) {} finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleRedeem = async (item: any) => {
    if (myPoints < item.cost_points) return Alert.alert('Insuficiente', 'Aún tienes que esforzarte más.');
    try {
      await redeemReward(item.id);
      Alert.alert('¡Canjeado!', `Disfruta de: ${item.title}`);
      fetchData();
    } catch (error: any) { Alert.alert('Error', error.response?.data?.error || 'No se pudo canjear'); }
  };

  const handleCreate = async () => {
    if(!title) return Alert.alert('Error', 'Escribe un título');
    try {
      await createReward({ title, cost_points: parseInt(cost) });
      setModalVisible(false);
      setTitle('');
      fetchData();
    } catch(e: any) { Alert.alert('Error', e.response?.data?.error || 'No se pudo crear'); }
  };
  
  const handleDelete = (id: string) => {
    Alert.alert('Borrar recompensa', '¿Estás seguro?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Borrar', style: 'destructive', onPress: async () => {
        try {
          await deleteReward(id);
          fetchData();
        } catch(e: any) { Alert.alert('Error', e.response?.data?.error || 'No se pudo borrar'); }
      }}
    ]);
  };

  const renderItem = ({ item }: any) => {
    const canAfford = myPoints >= item.cost_points;
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.title}>{item.title}</Text>
          <View style={{flexDirection: 'row', alignItems: 'center', gap: 12}}>
             <Text style={[styles.points, !canAfford && {color:'#9CA3AF'}]}>{item.cost_points} pts</Text>
             {isAdmin && (
                <TouchableOpacity onPress={() => handleDelete(item.id)}>
                   <Ionicons name="trash-outline" size={20} color="#EF4444" />
                </TouchableOpacity>
             )}
          </View>
        </View>
        <TouchableOpacity style={[styles.button, !canAfford && styles.buttonDisabled]} onPress={() => handleRedeem(item)}>
          <Text style={styles.buttonText}>{canAfford ? 'Canjear recompensa' : 'Puntos insuficientes'}</Text>
          {canAfford && <Ionicons name="arrow-forward" size={16} color="#fff" style={{marginLeft:8}}/>}
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Marketplace</Text>
          <Text style={styles.subtitle}>Tu saldo actual</Text>
        </View>
        <View style={styles.balanceBadge}>
          <Ionicons name="star" size={16} color="#F59E0B" />
          <Text style={styles.balanceText}>{myPoints}</Text>
        </View>
      </View>
      
      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#4F46E5"/> : (
        <FlatList data={rewards} renderItem={renderItem} keyExtractor={i => i.id} contentContainerStyle={styles.list} />
      )}

      {isAdmin && (
        <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
          <Ionicons name="add" size={32} color="#fff" />
        </TouchableOpacity>
      )}

      <Modal visible={modalVisible} animationType="fade" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>✨ Nueva Recompensa</Text>
            <TextInput style={styles.input} placeholder="¿Qué quieres ofrecer?" value={title} onChangeText={setTitle} />
            <TextInput style={styles.input} placeholder="Precio en puntos (ej. 100)" keyboardType="numeric" value={cost} onChangeText={setCost} />
            <View style={styles.modalButtons}>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}><Text>Cancelar</Text></TouchableOpacity>
              <TouchableOpacity onPress={handleCreate} style={styles.saveButton}><Text style={{color: '#fff', fontWeight:'bold'}}>Crear</Text></TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth:1, borderColor:'#E5E7EB' },
  headerTitle: { fontSize: 28, fontWeight: '900', color: '#111827' },
  subtitle: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  balanceBadge: { backgroundColor: '#FEF3C7', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, flexDirection: 'row', alignItems: 'center', gap: 6 },
  balanceText: { fontSize: 18, fontWeight: '900', color: '#B45309' },
  list: { padding: 16 },
  card: { backgroundColor: '#fff', padding: 24, borderRadius: 20, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  title: { flex: 1, fontSize: 18, fontWeight: 'bold', color:'#111827' },
  points: { fontSize: 20, color: '#10B981', fontWeight: '900' },
  button: { backgroundColor: '#4F46E5', flexDirection:'row', justifyContent:'center', alignItems:'center', paddingVertical: 14, borderRadius: 12 },
  buttonDisabled: { backgroundColor: '#E5E7EB' },
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  fab: { position: 'absolute', bottom: 24, right: 24, width: 64, height: 64, borderRadius: 32, backgroundColor: '#4F46E5', justifyContent: 'center', alignItems: 'center', shadowColor: '#4F46E5', shadowOpacity: 0.4, shadowRadius: 10, elevation: 5 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', padding: 32, borderTopLeftRadius: 32, borderTopRightRadius: 32 },
  modalTitle: { fontSize: 24, fontWeight: '800', marginBottom: 24, color:'#111827' },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, marginBottom: 16, fontSize:16 },
  modalButtons: { flexDirection: 'row', justifyContent: 'flex-end', gap: 16, marginTop: 10 },
  cancelButton: { padding: 16 },
  saveButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 12, minWidth:100, alignItems:'center' }
});
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Marketplace admin controls applied.")
