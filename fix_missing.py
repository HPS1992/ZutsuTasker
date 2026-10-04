import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Fix server.ts Express JSON limit
server_path = os.path.join(base_dir, "backend/src/server.ts")
with open(server_path, "r") as f:
    server = f.read()
server = server.replace("app.use(express.json());", "app.use(express.json({ limit: '50mb' }));")
with open(server_path, "w") as f:
    f.write(server)

# 2. Fix api.ts
api_path = os.path.join(base_dir, "mobile/src/services/api.ts")
with open(api_path, "r") as f:
    api = f.read()
if "getEquityStats" not in api:
    api += "\nexport const getEquityStats = async () => (await api.get('/stats/equity')).data;\n"
with open(api_path, "w") as f:
    f.write(api)

# 3. Update Group Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r") as f:
    schema = f.read()
if "default_assignment" not in schema:
    schema = schema.replace(
        "penalty_percentage Int      @default(50)",
        "penalty_percentage Int      @default(50)\n  default_assignment String   @default(\"RANDOM\")"
    )
    with open(schema_path, "w") as f:
        f.write(schema)

# 4. Update taskService.ts frequencies
task_service_path = os.path.join(base_dir, "backend/src/services/taskService.ts")
with open(task_service_path, "r") as f:
    ts = f.read()
if "BIWEEKLY" not in ts:
    ts = ts.replace(
        "else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);",
        "else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);\n      else if (freq === 'BIWEEKLY') nextDate.setDate(nextDate.getDate() + 14);\n      else if (freq === 'BIMONTHLY') nextDate.setMonth(nextDate.getMonth() + 2);\n      else if (freq === 'QUARTERLY') nextDate.setMonth(nextDate.getMonth() + 3);"
    )
    with open(task_service_path, "w") as f:
        f.write(ts)

# 5. Fix TasksScreen.tsx (uid -> id, Predefined tasks, Frequencies, Default mode)
tasks_screen = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView, Switch } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { Ionicons } from '@expo/vector-icons';
import { api, getMembers } from '../services/api';
import ConfettiCannon from 'react-native-confetti-cannon';
import { useAuth } from '../context/AuthContext';
import * as ImagePicker from 'expo-image-picker';

const PREDEFINED_TASKS = [
  { title: 'Bajar la basura', points: 5, icon: 'trash-outline' },
  { title: 'Hacer la cama', points: 5, icon: 'bed-outline' },
  { title: 'Fregar los platos', points: 15, icon: 'water-outline' },
  { title: 'Limpieza a fondo', points: 100, icon: 'sparkles-outline' },
];

const FREQUENCIES = [
  { id: 'ONCE', label: 'Una vez' }, { id: 'DAILY', label: 'Diaria' }, 
  { id: 'WEEKLY', label: 'Semanal' }, { id: 'BIWEEKLY', label: 'Quincenal' },
  { id: 'MONTHLY', label: 'Mensual' }, { id: 'BIMONTHLY', label: 'Bimensual' },
  { id: 'QUARTERLY', label: 'Trimestral' }
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
  const [assignType, setAssignType] = useState('RANDOM');
  const [fixedUser, setFixedUser] = useState<string | null>(null);
  const [requiresPhoto, setRequiresPhoto] = useState(false);
  const [startDateStr, setStartDateStr] = useState(new Date().toISOString().split('T')[0]);
  const [endDateStr, setEndDateStr] = useState('');

  useEffect(() => { 
    fetchTasks(); 
    getMembers().then(setMembers).catch(() => {});
    // Cargar método de asignación por defecto del grupo
    api.get('/group/settings').then(res => {
      if (res.data.default_assignment) setAssignType(res.data.default_assignment);
    }).catch(() => {});
  }, []);

  const handleComplete = async (item: any) => {
    if (item.template.requires_photo) {
      let result = await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5 });
      if (!result.canceled && result.assets[0].uri) {
        await completeTask(item.id, result.assets[0].uri);
      }
    } else {
      setShowConfetti(false);
      await completeTask(item.id);
      setShowConfetti(true);
    }
  };

  const handleCreate = async () => {
    if (!title) return;
    try {
      await api.post('/tasks', {
        title, points, frequency: freq, start_date: startDateStr, end_date: endDateStr || null,
        assignment_type: assignType, fixed_user_id: fixedUser, requires_photo: requiresPhoto
      });
      setModalVisible(false); fetchTasks();
    } catch (e: any) { alert('Error: ' + e.message); }
  };

  const applyPredefined = (item: any) => {
    setTitle(item.title);
    setPoints(item.points.toString());
  };

  const currentUserId = user?.id || user?.uid;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Planificación</Text>
      </View>
      <FlatList data={tasks} keyExtractor={t => t.id} renderItem={({item}) => <TaskCard item={item} currentUserId={currentUserId} onComplete={() => handleComplete(item)} />} contentContainerStyle={styles.list} />
      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}><Ionicons name="add" size={32} color="#fff" /></TouchableOpacity>
      {showConfetti && <ConfettiCannon count={100} origin={{x: -10, y: 0}} fallSpeed={2000} />}

      <Modal visible={modalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.modalTitle}>Nueva Tarea</Text>
              
              <Text style={styles.label}>Ideas Rápidas:</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{marginBottom: 16}}>
                {PREDEFINED_TASKS.map((pt, i) => (
                  <TouchableOpacity key={i} style={styles.predefCard} onPress={() => applyPredefined(pt)}>
                    <Ionicons name={pt.icon as any} size={24} color="#4F46E5" />
                    <Text style={styles.predefText}>{pt.title}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <Text style={styles.label}>Título Personalizado:</Text>
              <TextInput style={styles.input} placeholder="¿Qué hay que hacer?" value={title} onChangeText={setTitle} />
              
              <Text style={styles.label}>Puntos:</Text>
              <TextInput style={styles.input} keyboardType="numeric" value={points} onChangeText={setPoints} />
              
              <Text style={styles.label}>Frecuencia:</Text>
              <View style={styles.freqContainer}>
                {FREQUENCIES.map(f => (
                  <TouchableOpacity key={f.id} style={[styles.freqBtn, freq === f.id && styles.freqBtnActive]} onPress={() => setFreq(f.id)}>
                    <Text style={[styles.freqText, freq === f.id && styles.freqTextActive]}>{f.label}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <View style={{flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, backgroundColor: '#FCE7F3', padding: 16, borderRadius: 12}}>
                 <Text style={{fontWeight: 'bold', color: '#DB2777'}}>📸 Requiere Verificación por Foto</Text>
                 <Switch value={requiresPhoto} onValueChange={setRequiresPhoto} trackColor={{true: '#DB2777'}} />
              </View>

              <Text style={styles.label}>Asignación para esta tarea:</Text>
              <View style={styles.freqContainer}>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'MANUAL' && styles.freqBtnActive]} onPress={() => setAssignType('MANUAL')}><Text style={[styles.freqText, assignType === 'MANUAL' && styles.freqTextActive]}>Pizarra Común</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'RANDOM' && styles.freqBtnActive]} onPress={() => setAssignType('RANDOM')}><Text style={[styles.freqText, assignType === 'RANDOM' && styles.freqTextActive]}>Aleatorio</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, assignType === 'FIXED' && styles.freqBtnActive]} onPress={() => { setAssignType('FIXED'); setFixedUser(members[0]?.id); }}><Text style={[styles.freqText, assignType === 'FIXED' && styles.freqTextActive]}>Fija</Text></TouchableOpacity>
              </View>

              {assignType === 'FIXED' && (
                <View style={[styles.freqContainer, {marginTop: 8}]}>
                  {members.map(m => (<TouchableOpacity key={m.id} style={[styles.freqBtn, fixedUser === m.id && styles.freqBtnActive]} onPress={() => setFixedUser(m.id)}><Text style={[styles.freqText, fixedUser === m.id && styles.freqTextActive]}>👤 {m.name}</Text></TouchableOpacity>))}
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
  saveButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 12, minWidth:120, alignItems:'center' },
  predefCard: { backgroundColor: '#EEF2FF', padding: 16, borderRadius: 16, marginRight: 12, alignItems: 'center', minWidth: 100 },
  predefText: { color: '#4F46E5', fontWeight: '600', marginTop: 8, textAlign: 'center', fontSize: 12 }
});
"""
with open(os.path.join(base_dir, "mobile/src/screens/TasksScreen.tsx"), "w") as f:
    f.write(tasks_screen)

# 6. Fix ProfileScreen (Add group settings back)
profile_screen = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, TextInput, ScrollView, Platform, Modal, Share, Alert } from 'react-native';
import { api, getMembers, kickMember, transferPoints } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { triggerWowEffect } from '../utils/SoundHaptics';

export default function ProfileScreen() {
  const { logout } = useAuth();
  const navigation = useNavigation<any>();
  const [settings, setSettings] = useState<any>({ penalty_enabled: true, penalty_percentage: 50, name: '', id: '', default_assignment: 'RANDOM' });
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

  const openTransfer = (member: any) => {
    setSelectedMember(member); setTransferAmount(''); setTransferModal(true);
  };

  const handleTransfer = async () => {
    if (!transferAmount || isNaN(Number(transferAmount))) return;
    try {
      await transferPoints(selectedMember.id, transferAmount);
      await triggerWowEffect();
      setTransferModal(false);
      fetchData();
    } catch(e: any) { alert(e.response?.data?.error || 'Error'); }
  };

  const handleShareCode = async () => {
    try {
      const message = `¡Únete a mi piso en Zutsu Tasker!\\nEl código del grupo es: ${settings.id}`;
      if (Platform.OS === 'web') { alert(message); }
      else { await Share.share({ message }); }
    } catch (error) {}
  };

  const updateGroupAssignment = async (type: string) => {
    setSettings({...settings, default_assignment: type});
    try { await api.post('/group/settings', { default_assignment: type }); } catch(e){}
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}><Ionicons name="arrow-back" size={24} style={{marginRight: 16}}/></TouchableOpacity>
        <Text style={styles.headerTitle}>Mi Perfil</Text>
      </View>
      
      <ScrollView contentContainerStyle={styles.content}>
        
        <View style={{flexDirection: 'row', justifyContent: 'space-around', backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 24}}>
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 24}}>🔥</Text>
              <Text style={{fontSize: 20, fontWeight: 'bold'}}>{myStats.streak || 0}</Text>
              <Text style={{fontSize: 12, color: '#6B7280'}}>Racha (días)</Text>
           </View>
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 24}}>{myStats.is_mvp ? '👑' : '⭐'}</Text>
              <Text style={{fontSize: 20, fontWeight: 'bold'}}>{myStats.totalPoints || 0}</Text>
              <Text style={{fontSize: 12, color: '#6B7280'}}>Puntos</Text>
           </View>
        </View>

        <Text style={styles.sectionTitle}>Ajustes Personales</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View>
               <Text style={styles.settingText}>🌴 Modo Vacaciones</Text>
               <Text style={styles.helperText}>Pausa tareas y penalizaciones</Text>
            </View>
            <Switch value={vacationMode} onValueChange={(val) => { setVacationMode(val); api.post('/users/vacation', { is_on_vacation: val }); }} trackColor={{true: '#F59E0B'}} />
          </View>
        </View>

        {myStats.role === 'ADMIN' && (
          <>
            <Text style={styles.sectionTitle}>Gestión del Hogar (General)</Text>
            <View style={styles.card}>
              <TouchableOpacity style={styles.inviteBtn} onPress={handleShareCode}>
                <Ionicons name="share-social" size={24} color="#4F46E5" />
                <Text style={styles.inviteText}>Invitar al grupo (Código: {settings.id})</Text>
              </TouchableOpacity>

              <Text style={[styles.settingText, {marginTop: 16, marginBottom: 8}]}>Modo de Asignación por Defecto:</Text>
              <View style={{flexDirection: 'row', gap: 8}}>
                <TouchableOpacity style={[styles.freqBtn, settings.default_assignment === 'MANUAL' && styles.freqBtnActive]} onPress={() => updateGroupAssignment('MANUAL')}><Text style={[styles.freqText, settings.default_assignment === 'MANUAL' && styles.freqTextActive]}>Manual</Text></TouchableOpacity>
                <TouchableOpacity style={[styles.freqBtn, settings.default_assignment === 'RANDOM' && styles.freqBtnActive]} onPress={() => updateGroupAssignment('RANDOM')}><Text style={[styles.freqText, settings.default_assignment === 'RANDOM' && styles.freqTextActive]}>Aleatorio</Text></TouchableOpacity>
              </View>
            </View>
          </>
        )}

        <Text style={styles.sectionTitle}>Compañeros (Mercado Negro)</Text>
        <View style={styles.card}>
          {members.map((m, i) => (
            <TouchableOpacity key={m.id} style={[styles.memberRow, i < members.length-1 && {borderBottomWidth: 1, borderColor:'#F3F4F6'}]} onPress={() => openTransfer(m)} disabled={m.id === myStats.id}>
              <View>
                <Text style={styles.memberName}>{m.name} {m.is_mvp ? '👑' : ''} {m.id === myStats.id ? '(Tú)' : ''}</Text>
                <Text style={styles.memberPoints}>{m.points} pts acumulados</Text>
              </View>
              {m.id !== myStats.id && (
                <View style={{flexDirection: 'row', alignItems: 'center'}}>
                  <Text style={{color: '#4F46E5', fontWeight: 'bold', marginRight: 8}}>Sobornar</Text>
                  <Ionicons name="cash-outline" size={20} color="#4F46E5" />
                </View>
              )}
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity onPress={logout} style={styles.logoutButton}>
          <Text style={styles.logoutText}>Cerrar Sesión</Text>
        </TouchableOpacity>
      </ScrollView>

      <Modal visible={transferModal} animationType="slide" transparent={true}>
        <View style={{flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', padding: 20}}>
           <View style={{backgroundColor: '#fff', padding: 24, borderRadius: 24}}>
              <Text style={{fontSize: 20, fontWeight: 'bold', marginBottom: 16}}>Transferir a {selectedMember?.name}</Text>
              <TextInput style={{backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, fontSize: 18, marginBottom: 24}} placeholder="Ej. 50" keyboardType="numeric" value={transferAmount} onChangeText={setTransferAmount} />
              <View style={{flexDirection: 'row', justifyContent: 'flex-end', gap: 16}}>
                 <TouchableOpacity onPress={() => setTransferModal(false)} style={{padding: 16}}><Text>Cancelar</Text></TouchableOpacity>
                 <TouchableOpacity onPress={handleTransfer} style={{backgroundColor: '#4F46E5', padding: 16, borderRadius: 12}}><Text style={{color:'#fff', fontWeight:'bold'}}>Transferir</Text></TouchableOpacity>
              </View>
           </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', flexDirection: 'row', alignItems: 'center' },
  headerTitle: { fontSize: 24, fontWeight: '800' },
  content: { padding: 16 },
  sectionTitle: { fontSize: 14, fontWeight: 'bold', color: '#6B7280', marginBottom: 12, marginLeft: 4, textTransform: 'uppercase' },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 16 },
  memberRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12 },
  memberName: { fontSize: 16, fontWeight: 'bold' },
  memberPoints: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  settingText: { fontSize: 16, fontWeight: 'bold', color: '#111827' },
  helperText: { fontSize: 12, color: '#6B7280', marginTop: 4 },
  inviteBtn: { backgroundColor: '#EEF2FF', padding: 16, borderRadius: 12, flexDirection: 'row', alignItems: 'center', gap: 12 },
  inviteText: { color: '#4F46E5', fontWeight: 'bold', fontSize: 16 },
  freqBtn: { paddingHorizontal: 16, paddingVertical: 10, borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 12 },
  freqBtnActive: { backgroundColor: '#EEF2FF', borderColor: '#4F46E5' },
  freqText: { color: '#6B7280', fontWeight: '600' },
  freqTextActive: { color: '#4F46E5' },
  logoutButton: { backgroundColor: '#FEE2E2', padding: 16, borderRadius: 16, alignItems: 'center', marginTop: 24, marginBottom: 40 },
  logoutText: { color: '#EF4444', fontWeight: 'bold', fontSize: 16 }
});
"""
with open(os.path.join(base_dir, "mobile/src/screens/ProfileScreen.tsx"), "w") as f:
    f.write(profile_screen)

print("Finished applying all fixes.")
