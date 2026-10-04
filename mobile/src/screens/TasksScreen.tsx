import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView, Switch, Platform, Image } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { Ionicons } from '@expo/vector-icons';
import { api, getMembers, getTasksHistory } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';
import { useAuth } from '../context/AuthContext';
import * as ImagePicker from 'expo-image-picker';
import { LinearGradient } from 'expo-linear-gradient';

const PREDEFINED_TASKS = [
  { title: 'Bajar la basura', points: 5, icon: 'trash' },
  { title: 'Hacer la cama', points: 5, icon: 'bed' },
  { title: 'Fregar platos', points: 15, icon: 'water' },
  { title: 'Aspirar la casa', points: 30, icon: 'hardware-chip' },
  { title: 'Limpieza a fondo', points: 100, icon: 'sparkles' },
];

const PREDEFINED_ROOMS = [{name: 'General', icon: 'home'}, {name: 'Cocina', icon: 'restaurant'}, {name: 'Baño', icon: 'water'}, {name: 'Salón', icon: 'tv'}, {name: 'Dormitorio', icon: 'bed'}, {name: 'Exterior', icon: 'leaf'}];
const TASK_ICONS = ['checkbox', 'trash', 'bed', 'water', 'shirt', 'paw', 'car', 'cart', 'hammer', 'book', 'barbell', 'restaurant'];
const FREQUENCIES = [
  { id: 'ONCE', label: 'Una vez' }, { id: 'DAILY', label: 'Diaria' }, 
  { id: 'WEEKLY', label: 'Semanal' }, { id: 'BIWEEKLY', label: 'Quincenal' },
  { id: 'MONTHLY', label: 'Mensual' }
];

export default function TasksScreen() {
  const { user } = useAuth();
  const { tasks, fetchTasks, completeTask } = useTaskStore();
  const [members, setMembers] = useState<any[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [historyModal, setHistoryModal] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [rooms, setRooms] = useState<any[]>([]);
  const [selectedRoomFilter, setSelectedRoomFilter] = useState<string | null>(null);
  
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('10');
  const [freq, setFreq] = useState('ONCE');
  const [assignType, setAssignType] = useState('RANDOM');
  const [fixedUser, setFixedUser] = useState<string | null>(null);
  const [requiresPhoto, setRequiresPhoto] = useState(false);
  const [iconName, setIconName] = useState('checkbox');
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [roomName, setRoomName] = useState('General');
  const [roomIcon, setRoomIcon] = useState('home');
  const [startDateStr, setStartDateStr] = useState(new Date().toISOString().split('T')[0]);

  const fetchRooms = async () => {
    try { const res = await api.get('/tasks/rooms/health'); setRooms(res.data); } catch (e) {}
  };

  useEffect(() => { 
    fetchTasks(); fetchRooms();
    getMembers().then(setMembers).catch(() => {});
    api.get('/group/settings').then(res => {
      if (res.data.default_assignment) setAssignType(res.data.default_assignment);
    }).catch(() => {});
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getTasksHistory();
      setHistory(data);
      setHistoryModal(true);
    } catch(e) {}
  };

  const handleComplete = async (item: any) => {
    try {
      if (item.template.requires_photo) {
        let result = await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5 });
        if (!result.canceled && result.assets[0].uri) {
          await completeTask(item.id, result.assets[0].uri); fetchRooms();
        }
      } else {
        setShowConfetti(false);
        await completeTask(item.id);
        fetchRooms();
        setShowConfetti(true);
      }
    } catch(e: any) { alert('Error: ' + (e.response?.data?.error || e.message)); }
  };

  const handlePickIconImage = async () => {
    let result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5, base64: true });
    if (!result.canceled && result.assets[0].base64) {
      setImageUri(`data:image/jpeg;base64,${result.assets[0].base64}`);
    }
  };

  const handleCreate = async () => {
    if (!title) return;
    try {
      await api.post('/tasks', {
        title, points, frequency: freq, start_date: startDateStr, end_date: null,
        assignment_type: assignType, fixed_user_id: fixedUser, requires_photo: requiresPhoto, icon_name: iconName, image_uri: imageUri, room_name: roomName, room_icon: roomIcon
      });
      setModalVisible(false); fetchTasks(); fetchRooms();
    } catch (e: any) { alert('Error: ' + e.message); }
  };

  const currentUserId = user?.id || user?.uid;

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#5B3DF5', '#957CFF']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
            <View>
              <Text style={styles.headerTitle}>Tareas</Text>
              <Text style={styles.subtitle}>¿Qué toca hacer hoy?</Text>
            </View>
            <TouchableOpacity onPress={loadHistory} style={styles.historyBtn}>
               <Ionicons name="time" size={24} color="#fff" />
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </LinearGradient>

      {/* ROOMS HEALTH BAR */}
      <View style={{ marginTop: -20, marginBottom: 10, zIndex: 10 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 20, gap: 12 }}>
          <TouchableOpacity onPress={() => setSelectedRoomFilter(null)} style={[styles.roomCard, !selectedRoomFilter && styles.roomCardActive]}>
             <Ionicons name="apps" size={24} color={!selectedRoomFilter ? '#fff' : '#64748B'} />
             <Text style={[styles.roomName, !selectedRoomFilter && {color: '#fff'}]}>Todas</Text>
          </TouchableOpacity>
          {rooms.map(r => {
             const isCritical = r.health <= 25;
             const isWarning = r.health > 25 && r.health <= 60;
             const color = isCritical ? '#EF4444' : (isWarning ? '#F59E0B' : '#10B981');
             const isActive = selectedRoomFilter === r.name;
             return (
               <TouchableOpacity key={r.name} onPress={() => setSelectedRoomFilter(isActive ? null : r.name)} style={[styles.roomCard, isActive && {backgroundColor: color, borderColor: color}]}>
                 <Ionicons name={r.icon as any} size={24} color={isActive ? '#fff' : color} />
                 <Text style={[styles.roomName, isActive && {color: '#fff'}]}>{r.name}</Text>
                 <View style={styles.healthBarBg}>
                   <View style={[styles.healthBarFill, { width: `${r.health}%`, backgroundColor: isActive ? '#fff' : color }]} />
                 </View>
                 {isCritical && !isActive && <Text style={{position: 'absolute', top: -5, right: -5, fontSize: 16}}>🦠</Text>}
               </TouchableOpacity>
             )
          })}
        </ScrollView>
      </View>

      <FlatList 
        data={selectedRoomFilter ? tasks.filter(t => t.template.room_name === selectedRoomFilter) : tasks} 
        keyExtractor={t => t.id} 
        renderItem={({item}) => <TaskCard item={item} currentUserId={currentUserId} onComplete={() => handleComplete(item)} />} 
        contentContainerStyle={styles.list} 
      />

      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
        <LinearGradient colors={['#F59E0B', '#EF4444']} style={styles.fabGradient}>
          <Ionicons name="add" size={32} color="#fff" />
        </LinearGradient>
      </TouchableOpacity>

      {showConfetti && <ConfettiCannon count={120} origin={{x: -10, y: 0}} fallSpeed={2000} />}

      {/* CREATE MODAL */}
      <Modal visible={modalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalDragHandle} />
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.modalTitle}>Nueva Tarea</Text>
              
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{marginBottom: 20}}>
                {PREDEFINED_TASKS.map((pt, i) => (
                  <TouchableOpacity key={i} style={styles.predefCard} onPress={() => {setTitle(pt.title); setPoints(pt.points.toString()); setIconName(pt.icon);}}>
                    <View style={styles.predefIconWrap}><Ionicons name={pt.icon as any} size={24} color="#6366F1" /></View>
                    <Text style={styles.predefText}>{pt.title}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <Text style={styles.label}>Título:</Text>
              <TextInput style={styles.input} placeholder="Ej: Fregar" value={title} onChangeText={setTitle} />
              
              <Text style={styles.label}>Puntos:</Text>
              <TextInput style={styles.input} keyboardType="numeric" value={points} onChangeText={setPoints} />
              
              <Text style={styles.label}>Habitación / Zona:</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{marginBottom: 20}}>
                {PREDEFINED_ROOMS.map(r => (
                  <TouchableOpacity key={r.name} style={[styles.freqBtn, roomName === r.name && styles.freqBtnActive]} onPress={() => {setRoomName(r.name); setRoomIcon(r.icon);}}>
                    <Ionicons name={r.icon as any} size={16} color={roomName === r.name ? '#5B3DF5' : '#64748B'} style={{marginRight: 6}} />
                    <Text style={[styles.freqText, roomName === r.name && styles.freqTextActive]}>{r.name}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <Text style={styles.label}>Icono de la Tarea:</Text>
              <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 20}}>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  {TASK_ICONS.map(ic => (
                    <TouchableOpacity key={ic} style={[styles.iconSelectBtn, iconName === ic && !imageUri && styles.iconSelectBtnActive]} onPress={() => {setIconName(ic); setImageUri(null);}}>
                      <Ionicons name={ic as any} size={28} color={iconName === ic && !imageUri ? '#5B3DF5' : '#94A3B8'} />
                    </TouchableOpacity>
                  ))}
                </ScrollView>
                <TouchableOpacity style={styles.imagePickBtn} onPress={handlePickIconImage}>
                  {imageUri ? <Image source={{uri: imageUri}} style={{width: 44, height: 44, borderRadius: 12}} /> : <Ionicons name="image" size={24} color="#64748B" />}
                </TouchableOpacity>
              </View>

              <Text style={styles.label}>Frecuencia:</Text>
              <View style={styles.freqContainer}>
                {FREQUENCIES.map(f => (
                  <TouchableOpacity key={f.id} style={[styles.freqBtn, freq === f.id && styles.freqBtnActive]} onPress={() => setFreq(f.id)}>
                    <Text style={[styles.freqText, freq === f.id && styles.freqTextActive]}>{f.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <View style={styles.photoSwitchBox}>
                 <Text style={styles.photoSwitchText}>📸 Requerir Foto</Text>
                 <Switch value={requiresPhoto} onValueChange={setRequiresPhoto} trackColor={{true: '#DB2777', false: '#CBD5E1'}} thumbColor="#fff" />
              </View>

              <Text style={styles.label}>Asignación:</Text>
              <View style={styles.freqContainer}>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'MANUAL' && styles.freqBtnActive]} onPress={() => setAssignType('MANUAL')}><Text style={[styles.freqText, assignType === 'MANUAL' && styles.freqTextActive]}>Pizarra Común</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'RANDOM' && styles.freqBtnActive]} onPress={() => setAssignType('RANDOM')}><Text style={[styles.freqText, assignType === 'RANDOM' && styles.freqTextActive]}>Aleatorio</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'FIXED' && styles.freqBtnActive]} onPress={() => { setAssignType('FIXED'); setFixedUser(members[0]?.id); }}><Text style={[styles.freqText, assignType === 'FIXED' && styles.freqTextActive]}>Fija</Text></TouchableOpacity>
              </View>

              {assignType === 'FIXED' && (
                <View style={[styles.freqContainer, {marginTop: 12}]}>
                  {members.map(m => (<TouchableOpacity key={m.id} style={[styles.freqBtn, fixedUser === m.id && styles.freqBtnActive]} onPress={() => setFixedUser(m.id)}><Text style={[styles.freqText, fixedUser === m.id && styles.freqTextActive]}>👤 {m.name}</Text></TouchableOpacity>))}
                </View>
              )}

              <View style={{height: 120}} /> 
            </ScrollView>

            <View style={styles.modalButtonsFixed}>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}><Text style={styles.cancelButtonText}>Cancelar</Text></TouchableOpacity>
              <TouchableOpacity onPress={handleCreate} style={{flex: 1}}>
                <LinearGradient colors={['#7055F6', '#5B3DF5']} style={styles.saveButton}>
                  <Text style={styles.saveButtonText}>Guardar Tarea</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* HISTORY MODAL */}
      <Modal visible={historyModal} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, {height: '90%'}]}>
             <View style={styles.modalDragHandle} />
            <View style={{flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20}}>
              <Text style={styles.modalTitle}>Historial</Text>
              <TouchableOpacity onPress={() => setHistoryModal(false)} style={{backgroundColor: '#F1F5F9', padding: 8, borderRadius: 100}}>
                <Ionicons name="close" size={24} color="#0F172A" />
              </TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false}>
              {history.map(item => (
                <View key={item.id} style={styles.historyCard}>
                  <View style={{flexDirection: 'row', justifyContent: 'space-between'}}>
                     <Text style={{fontSize: 16, fontWeight: 'bold', color: '#0F172A'}}>{item.template?.title || 'Tarea borrada'}</Text>
                     <Text style={{color: '#D97706', fontWeight: '900'}}>+{item.points_awarded || item.template?.points} pts</Text>
                  </View>
                  <Text style={{color: '#64748B', marginTop: 4, fontWeight: '500'}}>👤 Realizada por: {item.assigned_to?.name || 'Desconocido'}</Text>
                  <Text style={{color: '#94A3B8', fontSize: 12, marginTop: 4}}>📅 {new Date(item.completed_at).toLocaleString('es-ES')}</Text>
                  <View style={{flexDirection: 'row', gap: 8, marginTop: 12}}>
                    {item.is_stolen && <Text style={styles.tagStolen}>🥷 Robada</Text>}
                    {item.penalty_applied && <Text style={styles.tagPenalty}>⚠️ Penalizó</Text>}
                  </View>
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
  headerGradient: { paddingBottom: 40, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, shadowColor: '#5B3DF5', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.8)', marginTop: 4, fontSize: 16, fontWeight: '500' },
  historyBtn: { backgroundColor: 'rgba(255,255,255,0.2)', padding: 12, borderRadius: 100 },
  list: { padding: 20, paddingBottom: 120 },
  fab: { position: 'absolute', bottom: Platform.OS==='web'? 80 : 100, right: 20, shadowColor: '#EF4444', shadowOpacity: 0.3, shadowRadius: 15, shadowOffset: { width: 0, height: 8 }, borderRadius: 32, backgroundColor: 'transparent' },
  fabGradient: { width: 64, height: 64, borderRadius: 32, justifyContent: 'center', alignItems: 'center' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', paddingHorizontal: 24, paddingTop: 12, borderTopLeftRadius: 40, borderTopRightRadius: 40, maxHeight: '90%' },
  modalDragHandle: { width: 40, height: 5, backgroundColor: '#E2E8F0', borderRadius: 10, alignSelf: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 28, fontWeight: '900', color: '#0F172A', marginBottom: 24, letterSpacing: -0.5 },
  label: { fontSize: 15, fontWeight: '700', color: '#475569', marginBottom: 10, marginTop: 20, textTransform: 'uppercase', letterSpacing: 1 },
  predefCard: { backgroundColor: '#F8FAFC', padding: 12, borderRadius: 20, marginRight: 12, alignItems: 'center', minWidth: 100, borderWidth: 1, borderColor: '#F1F5F9' },
  predefIconWrap: { backgroundColor: '#E8DEFF', padding: 12, borderRadius: 16, marginBottom: 8 },
  predefText: { color: '#5B3DF5', fontWeight: '800', textAlign: 'center', fontSize: 13 },
  input: { backgroundColor: '#F8FAFC', padding: 18, borderRadius: 16, fontSize: 16, borderWidth: 1, borderColor: '#E2E8F0', color: '#0F172A', fontWeight: '500' },
  freqContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  freqBtn: { paddingHorizontal: 18, paddingVertical: 12, borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 100, backgroundColor: '#fff' },
  freqBtnActive: { backgroundColor: '#E8DEFF', borderColor: '#5B3DF5' },
  freqText: { color: '#64748B', fontWeight: '700' },
  freqTextActive: { color: '#5B3DF5' },
  photoSwitchBox: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 24, backgroundColor: '#FDF2F8', padding: 20, borderRadius: 20, borderWidth: 1, borderColor: '#FCE7F3' },
  photoSwitchText: { fontWeight: '800', color: '#BE185D', fontSize: 16 },
  modalButtonsFixed: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: '#fff', padding: 24, flexDirection: 'row', gap: 16, borderTopWidth: 1, borderColor: '#F1F5F9', paddingBottom: Platform.OS === 'ios' ? 40 : 24 },
  cancelButton: { paddingVertical: 16, paddingHorizontal: 24, borderRadius: 16, backgroundColor: '#F1F5F9' },
  cancelButtonText: { color: '#475569', fontWeight: '700', fontSize: 16 },
  saveButton: { paddingVertical: 16, borderRadius: 16, alignItems: 'center' },
  saveButtonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  historyCard: { backgroundColor: '#fff', padding: 20, borderRadius: 20, marginBottom: 16, borderWidth: 1, borderColor: '#F1F5F9', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 10, shadowOffset: {width: 0, height: 5} },
  tagStolen: { backgroundColor: '#E8DEFF', color: '#5B3DF5', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 100, fontSize: 12, fontWeight: '800' },
  tagPenalty: { backgroundColor: '#FEE2E2', color: '#B91C1C', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 100, fontSize: 12, fontWeight: '800' },

  roomCard: { backgroundColor: '#fff', padding: 12, borderRadius: 20, borderWidth: 1, borderColor: '#F1F5F9', alignItems: 'center', minWidth: 80, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10 },
  roomCardActive: { backgroundColor: '#5B3DF5', borderColor: '#5B3DF5' },
  roomName: { fontSize: 12, fontWeight: '800', color: '#64748B', marginTop: 4, marginBottom: 8 },
  healthBarBg: { width: '100%', height: 6, backgroundColor: '#F1F5F9', borderRadius: 10, overflow: 'hidden' },
  healthBarFill: { height: '100%', borderRadius: 10 },
  iconSelectBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F8FAFC', marginRight: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  iconSelectBtnActive: { backgroundColor: '#E8DEFF', borderColor: '#5B3DF5' },
  imagePickBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F1F5F9', borderWidth: 1, borderColor: '#E2E8F0', borderStyle: 'dashed', justifyContent: 'center', alignItems: 'center', width: 48, height: 48, marginLeft: 8 },
});
