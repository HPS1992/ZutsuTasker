import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile"
files = {}

# 5. MarketScreen.tsx
files["src/screens/MarketScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, ActivityIndicator, Modal, TextInput, Platform, ScrollView, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getRewards, createReward, deleteReward, redeemReward, getRedemptions, completeRedemption, getRewardsHistory, api } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';
import { useAuth } from '../context/AuthContext';
import { triggerWowEffect } from '../utils/SoundHaptics';
import { LinearGradient } from 'expo-linear-gradient';

export default function MarketScreen() {
  const { user } = useAuth();
  const [rewards, setRewards] = useState<any[]>([]);
  const [redemptions, setRedemptions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [historyModal, setHistoryModal] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
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
    try { await createReward({ title, cost_points: parseInt(cost) }); setModalVisible(false); setTitle(''); setCost(''); fetchData(); } 
    catch(e: any) { alert(e.response?.data?.error || 'Error al crear'); }
  };

  const handleRedeem = async (id: string) => {
    try { await redeemReward(id); await triggerWowEffect(); setShowConfetti(true); fetchData(); setTimeout(() => setShowConfetti(false), 3000); } 
    catch(e: any) { alert(e.response?.data?.error || 'Puntos insuficientes'); }
  };

  const handleCompleteRedemption = async (id: string) => {
    try { await completeRedemption(id); await triggerWowEffect(); fetchData(); } 
    catch(e: any) { alert(e.response?.data?.error || 'Error'); }
  };

  const handleDelete = async (id: string) => {
    const confirmDelete = async () => {
      try { await deleteReward(id); fetchData(); } catch(e: any) { alert(e.response?.data?.error || 'Error'); }
    };
    if (Platform.OS === 'web') { if (window.confirm('¿Borrar recompensa?')) await confirmDelete(); } 
    else { Alert.alert('Borrar', '¿Seguro?', [ { text: 'Cancelar', style: 'cancel' }, { text: 'Borrar', style: 'destructive', onPress: confirmDelete } ]); }
  };

  const loadHistory = async () => {
    try { setHistory(await getRewardsHistory()); setHistoryModal(true); } catch(e) {}
  };

  const renderReward = ({ item }: any) => (
    <View style={styles.card}>
      <View style={{flex: 1}}>
         <Text style={styles.title}>{item.title}</Text>
         <View style={styles.pointsPill}>
            <Text style={styles.points}>⭐ {item.cost_points} pts</Text>
         </View>
      </View>
      <View style={{flexDirection: 'row', gap: 10, alignItems: 'center'}}>
        <TouchableOpacity onPress={() => handleRedeem(item.id)}>
          <LinearGradient colors={['#10B981', '#059669']} style={styles.redeemButton}>
            <Text style={styles.redeemText}>Comprar</Text>
          </LinearGradient>
        </TouchableOpacity>
        {isAdmin && (
          <TouchableOpacity onPress={() => handleDelete(item.id)} style={styles.deleteBtn}>
            <Ionicons name="trash" size={20} color="#EF4444" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#F59E0B', '#D97706']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
            <View>
              <Text style={styles.headerTitle}>Bazar</Text>
              <Text style={styles.subtitle}>Date un capricho</Text>
            </View>
            <TouchableOpacity onPress={loadHistory} style={styles.historyBtn}>
               <Ionicons name="time" size={24} color="#fff" />
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </LinearGradient>

      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#F59E0B"/> : (
        <FlatList
          ListHeaderComponent={
            redemptions.length > 0 ? (
              <View style={styles.pendingSection}>
                <Text style={styles.sectionTitle}>⏳ Tickets en tu poder</Text>
                {redemptions.map(r => (
                  <View key={r.id} style={styles.pendingCard}>
                    <View style={{flex: 1}}>
                      <Text style={styles.pendingTitle}>{r.reward.title}</Text>
                      <Text style={styles.pendingUser}>De: {r.user.id === currentUserId ? 'Ti' : r.user.name}</Text>
                    </View>
                    {r.user.id === currentUserId ? (
                      <TouchableOpacity style={styles.completeBtn} onPress={() => handleCompleteRedemption(r.id)}>
                        <Text style={styles.completeBtnText}>¡Canjear ahora!</Text>
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
          <LinearGradient colors={['#10B981', '#059669']} style={styles.fabGradient}>
             <Ionicons name="add" size={32} color="#fff" />
          </LinearGradient>
        </TouchableOpacity>
      )}

      {showConfetti && <ConfettiCannon count={100} origin={{x: -10, y: 0}} fallSpeed={2000} />}

      <Modal visible={modalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalDragHandle} />
            <Text style={styles.modalTitle}>Nuevo Premio</Text>
            <Text style={styles.label}>Nombre:</Text>
            <TextInput style={styles.input} placeholder="Ej: Pedir Pizza" value={title} onChangeText={setTitle} />
            <Text style={styles.label}>Coste en puntos:</Text>
            <TextInput style={styles.input} keyboardType="numeric" value={cost} onChangeText={setCost} />
            <View style={styles.modalButtonsFixed}>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}><Text style={styles.cancelButtonText}>Cancelar</Text></TouchableOpacity>
              <TouchableOpacity onPress={handleCreate} style={{flex: 1}}>
                <LinearGradient colors={['#10B981', '#059669']} style={styles.saveButton}>
                  <Text style={styles.saveButtonText}>Guardar</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={historyModal} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, {height: '90%'}]}>
            <View style={styles.modalDragHandle} />
            <View style={{flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20}}>
              <Text style={styles.modalTitle}>Historial</Text>
              <TouchableOpacity onPress={() => setHistoryModal(false)} style={styles.closeBtn}><Ionicons name="close" size={24} color="#0F172A" /></TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false}>
              {history.map(item => (
                <View key={item.id} style={styles.historyCard}>
                  <View style={{flexDirection: 'row', justifyContent: 'space-between'}}>
                     <Text style={{fontSize: 16, fontWeight: 'bold', color: '#0F172A'}}>{item.reward?.title || 'Borrado'}</Text>
                  </View>
                  <Text style={{color: '#64748B', marginTop: 4, fontWeight: '600'}}>👤 Disfrutado por: {item.user?.name}</Text>
                  <Text style={{color: '#94A3B8', fontSize: 12, marginTop: 4}}>📅 {new Date(item.redeemed_at).toLocaleString('es-ES')}</Text>
                  <Text style={styles.tagCompleted}>✅ Pagado y disfrutado</Text>
                </View>
              ))}
              <View style={{height: 100}} />
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  headerGradient: { paddingBottom: 24, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, shadowColor: '#D97706', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.8)', marginTop: 4, fontSize: 16, fontWeight: '500' },
  historyBtn: { backgroundColor: 'rgba(255,255,255,0.2)', padding: 12, borderRadius: 100 },
  list: { padding: 20, paddingBottom: 120 },
  pendingSection: { marginBottom: 24 },
  sectionTitle: { fontSize: 13, fontWeight: '900', color: '#94A3B8', marginBottom: 16, textTransform: 'uppercase', letterSpacing: 1 },
  pendingCard: { backgroundColor: '#FEF3C7', padding: 20, borderRadius: 24, marginBottom: 12, flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderColor: '#FDE68A', shadowColor: '#D97706', shadowOpacity: 0.1, shadowRadius: 10 },
  pendingTitle: { fontSize: 18, fontWeight: '900', color: '#92400E' },
  pendingUser: { fontSize: 14, color: '#B45309', marginTop: 4, fontWeight: '600' },
  waitingText: { color: '#D97706', fontWeight: '800', fontSize: 13 },
  completeBtn: { backgroundColor: '#D97706', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 100 },
  completeBtnText: { color: '#fff', fontWeight: '800', fontSize: 14 },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 24, marginBottom: 16, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 15, elevation: 2 },
  title: { fontSize: 18, fontWeight: '800', color: '#0F172A', marginBottom: 8 },
  pointsPill: { backgroundColor: '#FEF3C7', alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 100 },
  points: { fontSize: 13, color: '#D97706', fontWeight: '800' },
  redeemButton: { paddingHorizontal: 20, paddingVertical: 12, borderRadius: 100 },
  redeemText: { color: '#fff', fontWeight: '800' },
  deleteBtn: { backgroundColor: '#FEE2E2', padding: 12, borderRadius: 100 },
  fab: { position: 'absolute', bottom: Platform.OS==='web'? 80 : 100, right: 20, shadowColor: '#10B981', shadowOpacity: 0.3, shadowRadius: 15, shadowOffset: { width: 0, height: 8 } },
  fabGradient: { width: 64, height: 64, borderRadius: 32, justifyContent: 'center', alignItems: 'center' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', paddingHorizontal: 24, paddingTop: 12, borderTopLeftRadius: 40, borderTopRightRadius: 40, maxHeight: '90%' },
  modalDragHandle: { width: 40, height: 5, backgroundColor: '#E2E8F0', borderRadius: 10, alignSelf: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 28, fontWeight: '900', color: '#0F172A', marginBottom: 24, letterSpacing: -0.5 },
  label: { fontSize: 14, fontWeight: '800', color: '#475569', marginBottom: 8, marginTop: 16, textTransform: 'uppercase' },
  input: { backgroundColor: '#F8FAFC', padding: 18, borderRadius: 16, fontSize: 16, borderWidth: 1, borderColor: '#E2E8F0', color: '#0F172A', fontWeight: '600' },
  modalButtonsFixed: { marginTop: 32, paddingBottom: Platform.OS === 'ios' ? 40 : 24, flexDirection: 'row', gap: 16 },
  cancelButton: { paddingVertical: 16, paddingHorizontal: 24, borderRadius: 16, backgroundColor: '#F1F5F9' },
  cancelButtonText: { color: '#475569', fontWeight: '800', fontSize: 16 },
  saveButton: { paddingVertical: 16, borderRadius: 16, alignItems: 'center' },
  saveButtonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  closeBtn: { backgroundColor: '#F1F5F9', padding: 8, borderRadius: 100 },
  historyCard: { backgroundColor: '#fff', padding: 20, borderRadius: 20, marginBottom: 16, borderWidth: 1, borderColor: '#F1F5F9', shadowColor: '#000', shadowOpacity: 0.02, shadowRadius: 10 },
  tagCompleted: { backgroundColor: '#D1FAE5', color: '#059669', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 100, fontSize: 12, fontWeight: '800', alignSelf: 'flex-start', marginTop: 12 }
});
"""

# 6. StatsScreen.tsx
files["src/screens/StatsScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, ActivityIndicator, Platform } from 'react-native';
import { getEquityStats } from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';

export default function StatsScreen() {
  const [stats, setStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getEquityStats().then(setStats).finally(() => setLoading(false)); }, []);

  const renderItem = ({ item, index }: any) => {
    const isFirst = index === 0;
    return (
      <View style={[styles.card, isFirst && styles.firstCard]}>
        <View style={styles.cardHeader}>
          <Text style={[styles.name, isFirst && {color:'#fff'}]}>{isFirst ? '👑 ' : ''}{item.name}</Text>
          <Text style={[styles.percentage, isFirst && {color:'#fff'}]}>{item.percentage}%</Text>
        </View>
        <View style={styles.barContainer}>
          {isFirst ? (
             <LinearGradient colors={['#FCD34D', '#F59E0B']} style={[styles.bar, { width: `${item.percentage}%` }]} />
          ) : (
             <LinearGradient colors={['#10B981', '#059669']} style={[styles.bar, { width: `${item.percentage}%` }]} />
          )}
        </View>
        <Text style={[styles.details, isFirst && {color:'rgba(255,255,255,0.8)'}]}>Lleva {item.points} puntos globales generados en la casa</Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#0F172A', '#1E293B']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
             <Text style={styles.headerTitle}>Equilibrio</Text>
             <Text style={styles.subtitle}>¿Quién se está escaqueando?</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>

      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#6366F1"/> : (
        <FlatList data={stats.sort((a,b)=>b.points-a.points)} renderItem={renderItem} keyExtractor={i => i.name} contentContainerStyle={styles.list} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  headerGradient: { paddingBottom: 32, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 40, borderBottomRightRadius: 40, shadowColor: '#0F172A', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24 },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.7)', marginTop: 4, fontSize: 16, fontWeight: '600' },
  list: { padding: 20, paddingTop: 32, paddingBottom: 100 },
  card: { backgroundColor: '#fff', padding: 24, borderRadius: 32, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 15, elevation: 2, borderWidth: 1, borderColor: '#F1F5F9' },
  firstCard: { backgroundColor: '#6366F1', shadowColor: '#6366F1', shadowOpacity: 0.3, borderColor: '#4F46E5' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20, alignItems: 'center' },
  name: { fontSize: 20, fontWeight: '900', color: '#0F172A' },
  percentage: { fontSize: 24, fontWeight: '900', color: '#0F172A' },
  barContainer: { height: 16, backgroundColor: 'rgba(0,0,0,0.06)', borderRadius: 100, overflow: 'hidden', marginBottom: 12 },
  bar: { height: '100%', borderRadius: 100 },
  details: { fontSize: 13, color: '#64748B', fontWeight: '600' }
});
"""

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("UI Phase 2 complete.")
