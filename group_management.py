import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Auth Routes (Remove auto-join)
files["backend/src/routes/authRoutes.ts"] = """import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import jwt from 'jsonwebtoken';

const router = Router();
const prisma = new PrismaClient();

router.post('/register', async (req, res) => {
  try {
    const { email, name, firebase_uid } = req.body;
    const user = await prisma.user.create({ data: { email, name } });
    res.json(user);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

router.post('/local-register', async (req, res) => {
  try {
    const { email, name, password } = req.body;
    let user = await prisma.user.findUnique({ where: { email } });
    if (!user) {
      user = await prisma.user.create({ data: { email, name } });
      // YA NO HAY AUTO-JOIN. El usuario debe crear o unirse a un grupo.
    }
    const token = jwt.sign({ id: user.id, email: user.email }, 'MOCK_SECRET');
    res.json({ user, token });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

router.post('/local-login', async (req, res) => {
  try {
    const { email } = req.body;
    const user = await prisma.user.findUnique({ where: { email } });
    if (!user) return res.status(404).json({ error: 'Usuario no encontrado' });
    
    const token = jwt.sign({ id: user.id, email: user.email }, 'MOCK_SECRET');
    res.json({ user, token });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

export default router;
"""

# 2. Update Group Routes (Create, Join, Members, Kick)
files["backend/src/routes/groupRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

// Obtener ajustes del grupo
router.get('/settings', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id }, include: { group: true } });
    if (!member) return res.status(404).json({ error: 'Grupo no encontrado' });
    res.json({ ...member.group, role: member.role });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Guardar ajustes
router.post('/settings', requireAuth, async (req, res) => {
  try {
    const { penalty_enabled, penalty_percentage, name } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id, role: 'ADMIN' } });
    if (!member) return res.status(403).json({ error: 'No tienes permisos de admin' });

    const updated = await prisma.group.update({
      where: { id: member.group_id },
      data: { 
        penalty_enabled: penalty_enabled !== undefined ? penalty_enabled : undefined, 
        penalty_percentage: penalty_percentage !== undefined ? parseInt(penalty_percentage) : undefined,
        name: name !== undefined ? name : undefined
      }
    });
    res.json(updated);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Crear un grupo nuevo
router.post('/create', requireAuth, async (req, res) => {
  try {
    const { name } = req.body;
    const group = await prisma.group.create({ data: { name } });
    await prisma.groupMember.create({
      data: { user_id: req.user.id, group_id: group.id, role: 'ADMIN', total_points: 0 }
    });
    res.json(group);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Unirse a un grupo mediante ID
router.post('/join', requireAuth, async (req, res) => {
  try {
    const { groupId } = req.body;
    const group = await prisma.group.findUnique({ where: { id: groupId } });
    if (!group) return res.status(404).json({ error: 'Código de grupo inválido' });

    await prisma.groupMember.create({
      data: { user_id: req.user.id, group_id: group.id, role: 'MEMBER', total_points: 0 }
    });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Listar miembros
router.get('/members', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(404).json({ error: 'No estás en un grupo' });

    const members = await prisma.groupMember.findMany({
      where: { group_id: member.group_id },
      include: { user: true }
    });
    res.json(members.map(m => ({ id: m.user.id, name: m.user.name, role: m.role, points: m.total_points })));
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Expulsar miembro
router.delete('/members/:userId', requireAuth, async (req, res) => {
  try {
    const adminMember = await prisma.groupMember.findFirst({ where: { user_id: req.user.id, role: 'ADMIN' } });
    if (!adminMember) return res.status(403).json({ error: 'No tienes permisos de admin' });

    await prisma.groupMember.delete({
      where: { user_id_group_id: { user_id: req.params.userId, group_id: adminMember.group_id } }
    });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

# 3. Update User Dashboard Route (Devolver groupId)
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
      name: user.name,
      totalPoints: member ? member.total_points : 0,
      streak: member ? member.streak_days : 0,
      groupName: member ? member.group.name : null,
      groupId: member ? member.group.id : null
    });
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

# 4. Update Frontend API
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
export const redeemReward = async (id: string) => (await api.post(`/rewards/${id}/redeem`)).data;
export const getEquityStats = async () => (await api.get(`/stats/equity`)).data;

// Group management
export const createGroup = async (name: string) => (await api.post('/group/create', { name })).data;
export const joinGroup = async (groupId: string) => (await api.post('/group/join', { groupId })).data;
export const getMembers = async () => (await api.get('/group/members')).data;
export const kickMember = async (userId: string) => (await api.delete(`/group/members/${userId}`)).data;
"""

# 5. Update HomeScreen (Handle No Group State)
files["mobile/src/screens/HomeScreen.tsx"] = """import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, ActivityIndicator, TouchableOpacity, TextInput, Alert } from 'react-native';
import { api, createGroup, joinGroup } from '../services/api';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { registerForPushNotificationsAsync } from '../services/notifications';

export default function HomeScreen() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const navigation = useNavigation<any>();

  // States for No Group
  const [newGroupName, setNewGroupName] = useState('');
  const [inviteCode, setInviteCode] = useState('');

  const fetchDashboard = () => {
    api.get('/users/dashboard')
      .then(res => setData(res.data))
      .catch(err => setError(err.message));
  };

  useFocusEffect(
    useCallback(() => {
      fetchDashboard();
    }, [])
  );

  useEffect(() => {
    registerForPushNotificationsAsync();
  }, []);

  const handleCreateGroup = async () => {
    if(!newGroupName) return Alert.alert('Error', 'Pon un nombre');
    try { await createGroup(newGroupName); fetchDashboard(); } 
    catch(e) { Alert.alert('Error', 'No se pudo crear'); }
  };

  const handleJoinGroup = async () => {
    if(!inviteCode) return Alert.alert('Error', 'Pon el código');
    try { await joinGroup(inviteCode); fetchDashboard(); } 
    catch(e) { Alert.alert('Error', 'Código inválido'); }
  };

  if (error) return <SafeAreaView style={styles.container}><Text style={{padding:20, color:'red'}}>Error cargando: {error}</Text></SafeAreaView>;
  if (!data) return <SafeAreaView style={styles.container}><ActivityIndicator style={{marginTop: 50}} color="#4F46E5" /></SafeAreaView>;

  // Si el usuario acaba de registrarse y no tiene grupo
  if (!data.groupId) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.noGroupContainer}>
          <Text style={styles.greeting}>Bienvenido, {data.name} 👋</Text>
          <Text style={styles.noGroupDesc}>Para empezar a usar Zutsu, necesitas crear un grupo para tu hogar o unirte a uno existente.</Text>
          
          <View style={styles.actionCard}>
            <Text style={styles.sectionTitle}>Crear un nuevo hogar</Text>
            <TextInput style={styles.input} placeholder="Ej. Piso Estudiantes" value={newGroupName} onChangeText={setNewGroupName} />
            <TouchableOpacity style={styles.primaryButton} onPress={handleCreateGroup}>
               <Text style={styles.buttonText}>Crear y ser Administrador</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.actionCard}>
            <Text style={styles.sectionTitle}>Unirse a un hogar</Text>
            <TextInput style={styles.input} placeholder="Código de invitación (ID)" value={inviteCode} onChangeText={setInviteCode} />
            <TouchableOpacity style={styles.secondaryButton} onPress={handleJoinGroup}>
               <Text style={[styles.buttonText, {color: '#4F46E5'}]}>Unirse al grupo</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
            <Text style={styles.greeting}>¡Hola, {data.name}! 🚀</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Ajustes')}><Ionicons name="settings-outline" size={28} color="#4F46E5"/></TouchableOpacity>
          </View>
          <Text style={styles.groupName}><Ionicons name="home" size={14}/> {data.groupName}</Text>
        </View>

        <View style={styles.wowCard}>
          <View style={styles.glassLayer}>
            <Text style={styles.wowTitle}>Tu contribución mensual</Text>
            <Text style={styles.wowPoints}>{data.totalPoints}</Text>
            <Text style={styles.wowSubtitle}>puntos acumulados</Text>
          </View>
        </View>

        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <Ionicons name="flame" size={32} color="#F59E0B" />
            <Text style={styles.statValue}>{data.streak}</Text>
            <Text style={styles.statLabel}>Racha Actual</Text>
          </View>
          <View style={styles.statBox}>
            <Ionicons name="trophy" size={32} color="#10B981" />
            <Text style={styles.statValue}>{data.totalPoints}</Text>
            <Text style={styles.statLabel}>Total Global</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  scrollContent: { padding: 24 },
  noGroupContainer: { padding: 24, flex: 1, justifyContent: 'center' },
  noGroupDesc: { fontSize: 16, color: '#6B7280', marginBottom: 32, lineHeight: 24 },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, marginBottom: 16, fontSize:16 },
  primaryButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#EEF2FF', padding: 16, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  header: { marginBottom: 32 },
  greeting: { fontSize: 32, fontWeight: '900', color: '#111827', letterSpacing: -0.5 },
  groupName: { fontSize: 16, color: '#6B7280', marginTop: 6, fontWeight:'500' },
  wowCard: { backgroundColor: '#4F46E5', borderRadius: 24, padding: 32, alignItems: 'center', marginBottom: 24 },
  glassLayer: { alignItems: 'center' },
  wowTitle: { color: '#E0E7FF', fontSize: 16, fontWeight: '600', textTransform:'uppercase', letterSpacing:1 },
  wowPoints: { color: '#fff', fontSize: 64, fontWeight: '900', marginVertical: 8 },
  wowSubtitle: { color: '#A5B4FC', fontSize: 16, fontWeight: '500' },
  statsGrid: { flexDirection: 'row', gap: 16, marginBottom: 32 },
  statBox: { flex: 1, backgroundColor: '#fff', padding: 20, borderRadius: 20, alignItems: 'center' },
  statValue: { fontSize: 24, fontWeight: 'bold', color: '#111827', marginTop: 12 },
  statLabel: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  actionCard: { backgroundColor: '#fff', padding: 20, borderRadius: 20, marginBottom: 20, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', color: '#111827', marginBottom: 16 },
});
"""

# 6. Update Profile Screen (Group Management)
files["mobile/src/screens/ProfileScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, Alert, TextInput, ScrollView } from 'react-native';
import { api, getMembers, kickMember } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import * as Clipboard from 'expo-clipboard';

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

  const handleCopyCode = async () => {
    // Si Clipboard estuviera instalado lo usaríamos. Como fallback, solo lo mostramos.
    Alert.alert('Código de Invitación', `Tu código es: ${settings.id}\\n\\nCompártelo para que otros se unan al hogar.`);
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
        <TouchableOpacity style={styles.inviteCard} onPress={handleCopyCode}>
          <Text style={styles.inviteText}>ID: {settings.id}</Text>
          <Ionicons name="share-outline" size={24} color="#4F46E5" />
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

        <Text style={styles.sectionTitle}>Reglas y Castigos (Solo Admin)</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={{flexDirection:'row', alignItems:'center'}}>
              <Ionicons name="warning" size={24} color="#DC2626" style={{marginRight:12}}/>
              <Text style={styles.settingText}>Penalización</Text>
            </View>
            <Switch disabled={!isAdmin} value={settings.penalty_enabled} onValueChange={v => saveGroupSettings({ penalty_enabled: v })} trackColor={{true: '#10B981'}} />
          </View>
          <Text style={styles.helperText}>Si una tarea se retrasa más de 2 días, restará puntos.</Text>
        </View>

        <Text style={styles.sectionTitle}>Preferencias Personales</Text>
        <View style={styles.card}>
           <View style={styles.row}>
            <View style={{flexDirection:'row', alignItems:'center'}}>
              <Ionicons name="notifications" size={24} color="#4F46E5" style={{marginRight:12}}/>
              <Text style={styles.settingText}>Notificaciones Push</Text>
            </View>
            <Switch value={pushEnabled} onValueChange={setPushEnabled} trackColor={{true: '#10B981'}} />
          </View>
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
  inviteCard: { backgroundColor: '#EEF2FF', padding: 20, borderRadius: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, borderWidth: 1, borderColor: '#C7D2FE' },
  inviteText: { fontSize: 16, fontWeight: 'bold', color: '#4F46E5' },
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

print("Panel de invitaciones y gestión de miembros completado.")
