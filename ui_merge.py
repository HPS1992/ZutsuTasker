import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile"

app_tsx = """import React from 'react';
import { Platform, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { BlurView } from 'expo-blur';

import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import TasksScreen from './src/screens/TasksScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import MarketScreen from './src/screens/MarketScreen';
import StatsScreen from './src/screens/StatsScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: '#6366F1',
        tabBarInactiveTintColor: '#94A3B8',
        tabBarStyle: {
          position: 'absolute',
          bottom: Platform.OS === 'web' ? 0 : 20,
          left: Platform.OS === 'web' ? 0 : 20,
          right: Platform.OS === 'web' ? 0 : 20,
          elevation: 0,
          backgroundColor: Platform.OS === 'web' ? '#ffffff' : 'rgba(255,255,255,0.9)',
          borderTopWidth: 0,
          height: 70,
          borderRadius: Platform.OS === 'web' ? 0 : 24,
          shadowColor: '#6366F1',
          shadowOffset: { width: 0, height: 10 },
          shadowOpacity: 0.1,
          shadowRadius: 20,
        },
        tabBarBackground: () => Platform.OS !== 'web' ? (
           <BlurView tint="light" intensity={80} style={{...StyleSheet.absoluteFillObject, borderRadius: 24, overflow: 'hidden'}} />
        ) : null,
        tabBarShowLabel: true,
        tabBarLabelStyle: { fontWeight: 'bold', fontSize: 11, paddingBottom: 10 },
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: any = 'home';
          if (route.name === 'Tareas') iconName = focused ? 'checkbox' : 'checkbox-outline';
          else if (route.name === 'Premios') iconName = focused ? 'gift' : 'gift-outline';
          else if (route.name === 'Equidad') iconName = focused ? 'pie-chart' : 'pie-chart-outline';
          else if (route.name === 'Perfil') iconName = focused ? 'person' : 'person-outline';
          
          return <Ionicons name={iconName} size={28} color={color} style={{ marginTop: 10 }} />;
        },
      })}
    >
      <Tab.Screen name="Tareas" component={TasksScreen} />
      <Tab.Screen name="Premios" component={MarketScreen} />
      <Tab.Screen name="Equidad" component={StatsScreen} />
      <Tab.Screen name="Perfil" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

function RootNavigator() {
  const { user, loading } = useAuth();
  if (loading) return null;
  
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#F8FAFC' } }}>
      {user ? (
        <Stack.Screen name="Main" component={MainTabs} />
      ) : (
        <>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
        </>
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <RootNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}
"""

task_card_tsx = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform, Alert, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTaskStore } from '../store/useTaskStore';
import { LinearGradient } from 'expo-linear-gradient';

export const TaskCard = ({ item, currentUserId, onComplete }: any) => {
  const { claimTask, stealTask, approveTask } = useTaskStore();
  const assignedUserId = typeof item.assigned_to === 'string' ? item.assigned_to : item.assigned_to?.id;
  const isMine = assignedUserId === currentUserId;
  const isPendingReview = item.status === 'PENDING_REVIEW';
  
  const hasBounty = item.bounty_points && item.bounty_points > item.template.points;
  const displayPoints = item.bounty_points || item.template.points;

  const handleClaim = async () => { try { await claimTask(item.id); } catch(e: any) { alert(e.message); } };
  const handleSteal = async () => {
    const confirmSteal = async () => { try { await stealTask(item.id); } catch(e: any) { alert(e.message); } };
    if (Platform.OS === 'web') { if (window.confirm('¿Robar esta tarea?')) await confirmSteal(); } 
    else { Alert.alert('Robar', '¿Seguro?', [{ text: 'Cancelar', style: 'cancel' }, { text: '¡Robar!', style: 'destructive', onPress: confirmSteal }]); }
  };
  const handleApprove = async () => { try { await approveTask(item.id); } catch(e: any) { alert(e.message); } };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.titleRow}>
          <View style={[styles.iconBox, item.template.image_uri && {padding: 0, backgroundColor: 'transparent'}]}>
            {item.template.image_uri ? (
               <Image source={{ uri: item.template.image_uri }} style={{width: 44, height: 44, borderRadius: 16}} />
            ) : (
               <Ionicons name={item.template.icon_name || 'checkbox'} size={24} color="#6366F1" />
            )}
          </View>
          <View style={{flex: 1}}>
            <Text style={styles.title}>{item.template.title}</Text>
            {item.template.requires_photo && <Text style={styles.photoRequiredText}>📸 Requiere Foto</Text>}
          </View>
        </View>
        <View style={[styles.pointsBadge, hasBounty && styles.bountyBadge]}>
          <Text style={[styles.pointsText, hasBounty && styles.bountyText]}>{hasBounty ? '🔥' : '⭐'} {displayPoints} pts</Text>
        </View>
      </View>

      <View style={styles.detailsRow}>
        <View style={[styles.infoChip, {backgroundColor: '#EEF2FF', borderColor: '#E0E7FF'}]}>
           <Ionicons name={item.template.room_icon || 'home'} size={14} color="#4F46E5" />
           <Text style={[styles.infoText, {color: '#4F46E5'}]}>{item.template.room_name || 'General'}</Text>
        </View>
        <View style={styles.infoChip}><Ionicons name="calendar-outline" size={14} color="#64748B" /><Text style={styles.infoText}>{new Date(item.due_date).toLocaleDateString()}</Text></View>
        {item.assigned_to ? (
          <View style={styles.infoChip}><Ionicons name="person-circle-outline" size={16} color="#64748B" /><Text style={[styles.infoText, isMine && {color: '#6366F1', fontWeight: 'bold'}]}>{isMine ? 'Tuya' : item.assigned_to.name}</Text></View>
        ) : (
          <View style={[styles.infoChip, { backgroundColor: '#FEF3C7', borderColor: '#FCD34D' }]}><Ionicons name="hand-right-outline" size={14} color="#D97706" /><Text style={[styles.infoText, {color: '#D97706', fontWeight: 'bold'}]}>¡Libre!</Text></View>
        )}
      </View>

      <View style={styles.actions}>
        {item.status === 'PENDING' && !item.assigned_to && (
          <TouchableOpacity onPress={handleClaim} style={{ flex: 1 }}><LinearGradient colors={['#6366F1', '#4F46E5']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>¡Me la pido!</Text></LinearGradient></TouchableOpacity>
        )}
        {item.status === 'PENDING' && item.assigned_to && (
          isMine ? (
            <TouchableOpacity onPress={onComplete} style={{ flex: 1 }}><LinearGradient colors={['#10B981', '#059669']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>Completar</Text></LinearGradient></TouchableOpacity>
          ) : (
            new Date(item.due_date) < new Date() && (
              <TouchableOpacity onPress={handleSteal} style={{ flex: 1 }}><LinearGradient colors={['#F43F5E', '#E11D48']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>🥷 ¡Robar! (+150%)</Text></LinearGradient></TouchableOpacity>
            )
          )
        )}
        {isPendingReview && (
          <View style={{ flex: 1, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
            <View style={[styles.primaryButton, { flex: 1, backgroundColor: '#FEF3C7' }]}><Text style={{ color: '#D97706', fontWeight: 'bold' }}>⏳ Revisando...</Text></View>
            {!isMine && <TouchableOpacity onPress={handleApprove} style={{ flex: 1 }}><LinearGradient colors={['#8B5CF6', '#7C3AED']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>✅ Aprobar</Text></LinearGradient></TouchableOpacity>}
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderRadius: 24, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(226, 232, 240, 0.8)', shadowColor: '#94A3B8', shadowOpacity: 0.1, shadowRadius: 20, shadowOffset: { width: 0, height: 10 }, elevation: 4 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  iconBox: { backgroundColor: '#EEF2FF', padding: 10, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 18, fontWeight: '800', color: '#0F172A', flexWrap: 'wrap', marginRight: 8 },
  photoRequiredText: { fontSize: 12, color: '#DB2777', fontWeight: 'bold', marginTop: 2 },
  pointsBadge: { backgroundColor: '#FEF3C7', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  bountyBadge: { backgroundColor: '#FEE2E2' },
  pointsText: { color: '#B45309', fontWeight: '900', fontSize: 14 },
  bountyText: { color: '#E11D48' },
  detailsRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  infoChip: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#F8FAFC', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: '#F1F5F9' },
  infoText: { color: '#64748B', fontSize: 13, fontWeight: '600' },
  actions: { flexDirection: 'row', gap: 10 },
  primaryButton: { paddingVertical: 14, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  primaryButtonText: { color: '#fff', fontWeight: '800', fontSize: 15, letterSpacing: 0.5 },
});
"""

tasks_screen_tsx = """import React, { useEffect, useState } from 'react';
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
      <LinearGradient colors={['#4F46E5', '#7C3AED']} style={styles.headerGradient}>
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
                    <Ionicons name={r.icon as any} size={16} color={roomName === r.name ? '#6366F1' : '#64748B'} style={{marginRight: 6}} />
                    <Text style={[styles.freqText, roomName === r.name && styles.freqTextActive]}>{r.name}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <Text style={styles.label}>Icono de la Tarea:</Text>
              <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 20}}>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  {TASK_ICONS.map(ic => (
                    <TouchableOpacity key={ic} style={[styles.iconSelectBtn, iconName === ic && !imageUri && styles.iconSelectBtnActive]} onPress={() => {setIconName(ic); setImageUri(null);}}>
                      <Ionicons name={ic as any} size={28} color={iconName === ic && !imageUri ? '#6366F1' : '#94A3B8'} />
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
                <LinearGradient colors={['#6366F1', '#4F46E5']} style={styles.saveButton}>
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
  headerGradient: { paddingBottom: 40, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, shadowColor: '#4F46E5', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.8)', marginTop: 4, fontSize: 16, fontWeight: '500' },
  historyBtn: { backgroundColor: 'rgba(255,255,255,0.2)', padding: 12, borderRadius: 100 },
  list: { padding: 20, paddingBottom: 120 },
  fab: { position: 'absolute', bottom: Platform.OS==='web'? 80 : 100, right: 20, shadowColor: '#EF4444', shadowOpacity: 0.3, shadowRadius: 15, shadowOffset: { width: 0, height: 8 } },
  fabGradient: { width: 64, height: 64, borderRadius: 32, justifyContent: 'center', alignItems: 'center' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(15, 23, 42, 0.6)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', paddingHorizontal: 24, paddingTop: 12, borderTopLeftRadius: 40, borderTopRightRadius: 40, maxHeight: '90%' },
  modalDragHandle: { width: 40, height: 5, backgroundColor: '#E2E8F0', borderRadius: 10, alignSelf: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 28, fontWeight: '900', color: '#0F172A', marginBottom: 24, letterSpacing: -0.5 },
  label: { fontSize: 15, fontWeight: '700', color: '#475569', marginBottom: 10, marginTop: 20, textTransform: 'uppercase', letterSpacing: 1 },
  predefCard: { backgroundColor: '#F8FAFC', padding: 12, borderRadius: 20, marginRight: 12, alignItems: 'center', minWidth: 100, borderWidth: 1, borderColor: '#F1F5F9' },
  predefIconWrap: { backgroundColor: '#EEF2FF', padding: 12, borderRadius: 16, marginBottom: 8 },
  predefText: { color: '#4F46E5', fontWeight: '800', textAlign: 'center', fontSize: 13 },
  input: { backgroundColor: '#F8FAFC', padding: 18, borderRadius: 16, fontSize: 16, borderWidth: 1, borderColor: '#E2E8F0', color: '#0F172A', fontWeight: '500' },
  freqContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  freqBtn: { paddingHorizontal: 18, paddingVertical: 12, borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 100, backgroundColor: '#fff' },
  freqBtnActive: { backgroundColor: '#EEF2FF', borderColor: '#6366F1' },
  freqText: { color: '#64748B', fontWeight: '700' },
  freqTextActive: { color: '#6366F1' },
  photoSwitchBox: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 24, backgroundColor: '#FDF2F8', padding: 20, borderRadius: 20, borderWidth: 1, borderColor: '#FCE7F3' },
  photoSwitchText: { fontWeight: '800', color: '#BE185D', fontSize: 16 },
  modalButtonsFixed: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: '#fff', padding: 24, flexDirection: 'row', gap: 16, borderTopWidth: 1, borderColor: '#F1F5F9', paddingBottom: Platform.OS === 'ios' ? 40 : 24 },
  cancelButton: { paddingVertical: 16, paddingHorizontal: 24, borderRadius: 16, backgroundColor: '#F1F5F9' },
  cancelButtonText: { color: '#475569', fontWeight: '700', fontSize: 16 },
  saveButton: { paddingVertical: 16, borderRadius: 16, alignItems: 'center' },
  saveButtonText: { color: '#fff', fontWeight: '800', fontSize: 16 },
  historyCard: { backgroundColor: '#fff', padding: 20, borderRadius: 20, marginBottom: 16, borderWidth: 1, borderColor: '#F1F5F9', shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 10, shadowOffset: {width: 0, height: 5} },
  tagStolen: { backgroundColor: '#F3E8FF', color: '#7E22CE', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 100, fontSize: 12, fontWeight: '800' },
  tagPenalty: { backgroundColor: '#FEE2E2', color: '#B91C1C', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 100, fontSize: 12, fontWeight: '800' },

  roomCard: { backgroundColor: '#fff', padding: 12, borderRadius: 20, borderWidth: 1, borderColor: '#F1F5F9', alignItems: 'center', minWidth: 80, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10 },
  roomCardActive: { backgroundColor: '#6366F1', borderColor: '#6366F1' },
  roomName: { fontSize: 12, fontWeight: '800', color: '#64748B', marginTop: 4, marginBottom: 8 },
  healthBarBg: { width: '100%', height: 6, backgroundColor: '#F1F5F9', borderRadius: 10, overflow: 'hidden' },
  healthBarFill: { height: '100%', borderRadius: 10 },
  iconSelectBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F8FAFC', marginRight: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  iconSelectBtnActive: { backgroundColor: '#EEF2FF', borderColor: '#6366F1' },
  imagePickBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F1F5F9', borderWidth: 1, borderColor: '#E2E8F0', borderStyle: 'dashed', justifyContent: 'center', alignItems: 'center', width: 48, height: 48, marginLeft: 8 },
});
"""

profile_screen_tsx = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, TextInput, ScrollView, Platform, Modal, Share } from 'react-native';
import { api, getMembers, transferPoints } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { triggerWowEffect } from '../utils/SoundHaptics';
import { LinearGradient } from 'expo-linear-gradient';

export default function ProfileScreen() {
  const { logout } = useAuth();
  const [settings, setSettings] = useState<any>({ penalty_enabled: true, penalty_percentage: 50, id: '', default_assignment: 'RANDOM' });
  const [members, setMembers] = useState<any[]>([]);
  const [myStats, setMyStats] = useState<any>({});
  const [transferModal, setTransferModal] = useState(false);
  const [selectedMember, setSelectedMember] = useState<any>(null);
  const [transferAmount, setTransferAmount] = useState('');
  const [vacationMode, setVacationMode] = useState(false);

  const fetchData = () => {
    api.get('/group/settings').then(res => setSettings(res.data)).catch(()=>{});
    getMembers().then(res => setMembers(res)).catch(()=>{});
    api.get('/users/dashboard').then(res => { setMyStats(res.data); setVacationMode(res.data.is_on_vacation); }).catch(()=>{});
  };

  useEffect(() => { fetchData(); }, []);

  const openTransfer = (member: any) => { setSelectedMember(member); setTransferAmount(''); setTransferModal(true); };
  const handleTransfer = async () => {
    if (!transferAmount) return;
    try { await transferPoints(selectedMember.id, transferAmount); await triggerWowEffect(); setTransferModal(false); fetchData(); } 
    catch(e: any) { alert(e.response?.data?.error || 'Error'); }
  };
  const handleShareCode = async () => {
    try {
      const message = `¡Únete a mi piso en Zutsu Tasker!\\nEl código es: ${settings.id}`;
      if (Platform.OS === 'web') alert(message); else await Share.share({ message });
    } catch (error) {}
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#4F46E5', '#7C3AED']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
            <Text style={styles.headerTitle}>Mi Perfil</Text>
            <Text style={styles.subtitle}>Gestión y configuración</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>

      <ScrollView contentContainerStyle={styles.content}>
        
        {/* Glowing Stats Card */}
        <LinearGradient colors={['#0F172A', '#1E293B']} style={styles.statsCard}>
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 32}}>🔥</Text>
              <Text style={styles.statsValue}>{myStats.streak || 0}</Text>
              <Text style={styles.statsLabel}>Racha Días</Text>
           </View>
           <View style={{width: 1, backgroundColor: 'rgba(255,255,255,0.1)'}} />
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 32}}>{myStats.is_mvp ? '👑' : '⭐'}</Text>
              <Text style={styles.statsValue}>{myStats.totalPoints || 0}</Text>
              <Text style={styles.statsLabel}>Puntos Totales</Text>
           </View>
        </LinearGradient>

        <Text style={styles.sectionTitle}>Ajustes Personales</Text>
        <View style={styles.card}>
          <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
            <View>
               <Text style={styles.settingText}>🌴 Modo Vacaciones</Text>
               <Text style={styles.helperText}>Pausa tareas temporalmente</Text>
            </View>
            <Switch value={vacationMode} onValueChange={(val) => { setVacationMode(val); api.post('/users/vacation', { is_on_vacation: val }); }} trackColor={{true: '#F59E0B'}} />
          </View>
        </View>

        {myStats.role === 'ADMIN' && (
          <>
            <Text style={styles.sectionTitle}>Gestión del Hogar</Text>
            <View style={styles.card}>
              <TouchableOpacity onPress={handleShareCode}>
                <LinearGradient colors={['#EEF2FF', '#E0E7FF']} style={styles.inviteBtn}>
                  <Ionicons name="share-social" size={24} color="#6366F1" />
                  <Text style={styles.inviteText}>Invitar al grupo</Text>
                </LinearGradient>
              </TouchableOpacity>
              <Text style={{textAlign: 'center', marginTop: 8, color: '#94A3B8', fontWeight: 'bold', fontSize: 12}}>ID: {settings.id}</Text>
            </View>
          </>
        )}

        <Text style={styles.sectionTitle}>Mercado Negro</Text>
        <View style={styles.card}>
          {members.map((m, i) => (
            <TouchableOpacity key={m.id} style={[styles.memberRow, i < members.length-1 && {borderBottomWidth: 1, borderColor:'#F1F5F9'}]} onPress={() => openTransfer(m)} disabled={m.id === myStats.id}>
              <View>
                <Text style={styles.memberName}>{m.name} {m.is_mvp ? '👑' : ''} {m.id === myStats.id ? '(Tú)' : ''}</Text>
                <Text style={styles.memberPoints}>{m.points} pts acumulados</Text>
              </View>
              {m.id !== myStats.id && (
                <View style={styles.bribeBtn}>
                  <Text style={styles.bribeText}>Sobornar</Text>
                </View>
              )}
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity onPress={logout} style={styles.logoutButton}>
          <Text style={styles.logoutText}>Cerrar Sesión</Text>
        </TouchableOpacity>
        
        <View style={{height: 120}} />
      </ScrollView>

      <Modal visible={transferModal} animationType="slide" transparent={true}>
        <View style={{flex: 1, backgroundColor: 'rgba(15,23,42,0.8)', justifyContent: 'center', padding: 24}}>
           <View style={{backgroundColor: '#fff', padding: 32, borderRadius: 32}}>
              <Text style={{fontSize: 24, fontWeight: '900', color: '#0F172A', marginBottom: 20}}>Sobornar a {selectedMember?.name}</Text>
              <TextInput style={{backgroundColor: '#F8FAFC', padding: 20, borderRadius: 16, fontSize: 20, borderWidth: 1, borderColor: '#E2E8F0', marginBottom: 32, fontWeight: 'bold', color: '#6366F1'}} placeholder="Puntos a enviar..." keyboardType="numeric" value={transferAmount} onChangeText={setTransferAmount} />
              <View style={{flexDirection: 'row', justifyContent: 'flex-end', gap: 16}}>
                 <TouchableOpacity onPress={() => setTransferModal(false)} style={{padding: 16}}><Text style={{fontWeight: '700', color: '#64748B'}}>Cancelar</Text></TouchableOpacity>
                 <TouchableOpacity onPress={handleTransfer}>
                    <LinearGradient colors={['#6366F1', '#4F46E5']} style={{paddingVertical: 16, paddingHorizontal: 32, borderRadius: 16}}>
                      <Text style={{color:'#fff', fontWeight:'800'}}>Enviar 💸</Text>
                    </LinearGradient>
                 </TouchableOpacity>
              </View>
           </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  headerGradient: { paddingBottom: 24, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, shadowColor: '#4F46E5', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24 },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.8)', marginTop: 4, fontSize: 16, fontWeight: '500' },
  content: { padding: 20, paddingTop: 32 },
  sectionTitle: { fontSize: 13, fontWeight: '800', color: '#94A3B8', marginBottom: 12, marginLeft: 8, textTransform: 'uppercase', letterSpacing: 1 },
  statsCard: { padding: 24, borderRadius: 32, flexDirection: 'row', justifyContent: 'space-evenly', marginBottom: 32, shadowColor: '#0F172A', shadowOpacity: 0.2, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  statsValue: { color: '#fff', fontSize: 24, fontWeight: '900', marginTop: 8 },
  statsLabel: { color: '#94A3B8', fontSize: 12, fontWeight: '700', marginTop: 4, textTransform: 'uppercase' },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 24, marginBottom: 24, shadowColor: '#000', shadowOpacity: 0.02, shadowRadius: 10, elevation: 1 },
  memberRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 16 },
  memberName: { fontSize: 16, fontWeight: '800', color: '#0F172A' },
  memberPoints: { fontSize: 13, color: '#64748B', marginTop: 4, fontWeight: '600' },
  bribeBtn: { backgroundColor: '#F3E8FF', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 100 },
  bribeText: { color: '#7C3AED', fontWeight: '800', fontSize: 13 },
  settingText: { fontSize: 16, fontWeight: '800', color: '#0F172A' },
  helperText: { fontSize: 13, color: '#64748B', marginTop: 4, fontWeight: '500' },
  inviteBtn: { padding: 20, borderRadius: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12 },
  inviteText: { color: '#4F46E5', fontWeight: '900', fontSize: 16 },
  logoutButton: { backgroundColor: '#FEE2E2', padding: 20, borderRadius: 20, alignItems: 'center', marginTop: 16 },
  logoutText: { color: '#E11D48', fontWeight: '900', fontSize: 16, letterSpacing: 0.5 }
});
"""

files = {
    "App.tsx": app_tsx,
    "src/components/TaskCard.tsx": task_card_tsx,
    "src/screens/TasksScreen.tsx": tasks_screen_tsx,
    "src/screens/ProfileScreen.tsx": profile_screen_tsx
}

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Massive UI Merge Completed.")
