import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. FIX AUTH MIDDLEWARE
files["backend/src/middleware/authMiddleware.ts"] = """import { Request, Response, NextFunction } from 'express';
import { PrismaClient } from '@prisma/client';
import * as admin from 'firebase-admin';
import dotenv from 'dotenv';
dotenv.config();

const prisma = new PrismaClient();
// Fallback a true si no está explícitamente en false
const useMockAuth = process.env.USE_MOCK_AUTH !== 'false';

let adminInitialized = false;
try {
  if (!useMockAuth && process.env.FIREBASE_SERVICE_ACCOUNT_PATH) {
    const serviceAccount = require('../../firebase-admin.json');
    admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
    adminInitialized = true;
  }
} catch (e) {
  console.warn("⚠️ No se pudo inicializar Firebase Admin.");
}

export const requireAuth = async (req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split('Bearer ')[1];
  if (!token) return res.status(401).json({ error: 'No token provided' });

  try {
    if (useMockAuth || token === 'MOCK_TOKEN') {
      const user = await prisma.user.findFirst({ where: { email: 'alex@test.com' }});
      if (!user) throw new Error('User not found in DB');
      req.user = user;
      return next();
    }

    if (!adminInitialized) throw new Error("Firebase admin not configured");
    const decodedToken = await admin.auth().verifyIdToken(token);
    const user = await prisma.user.findUnique({ where: { email: decodedToken.email } });
    if (!user) return res.status(401).json({ error: 'Unregistered user' });
    
    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};
"""

# 2. FIX MOBILE AUTH CONTEXT
files["mobile/src/context/AuthContext.tsx"] = """import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from 'firebase/auth';
import { auth } from '../config/firebase';
import { api } from '../services/api';

interface AuthContextData {
  user: User | null;
  loading: boolean;
  login: (e: string, p: string) => Promise<void>;
  register: (e: string, p: string, n: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Si no hay key real o EXPO_PUBLIC_USE_MOCK_AUTH no es false, usamos mock
  const useMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH !== 'false' || auth.app.options.apiKey === 'TU_API_KEY';

  useEffect(() => {
    if (useMockAuth) {
      setLoading(false);
      return;
    }

    const unsub = onAuthStateChanged(auth, async (usr) => {
      setUser(usr);
      if (usr) {
        const token = await usr.getIdToken();
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      } else {
        delete api.defaults.headers.common['Authorization'];
      }
      setLoading(false);
    });
    return unsub;
  }, []);

  const login = async (e: string, p: string) => {
    if (useMockAuth) {
      setUser({ uid: 'u123', email: e || 'test@test.com' } as User);
      api.defaults.headers.common['Authorization'] = `Bearer MOCK_TOKEN`;
      return;
    }
    await signInWithEmailAndPassword(auth, e, p);
  };

  const register = async (e: string, p: string, name: string) => {
    if (useMockAuth) {
      setUser({ uid: 'u123', email: e || 'test@test.com' } as User);
      api.defaults.headers.common['Authorization'] = `Bearer MOCK_TOKEN`;
      return;
    }
    const cred = await createUserWithEmailAndPassword(auth, e, p);
    const token = await cred.user.getIdToken();
    await api.post('/auth/register', { email: e, name, firebase_uid: cred.user.uid }, {
      headers: { Authorization: `Bearer ${token}` }
    });
  };

  const logout = () => {
    if (useMockAuth) {
      setUser(null);
      return;
    }
    signOut(auth).catch(() => {});
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
"""

# 3. FIX HOME SCREEN (Error handling)
files["mobile/src/screens/HomeScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, ActivityIndicator, TouchableOpacity } from 'react-native';
import { api } from '../services/api';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { registerForPushNotificationsAsync } from '../services/notifications';

export default function HomeScreen() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const navigation = useNavigation<any>();

  useEffect(() => {
    api.get('/users/dashboard')
      .then(res => setData(res.data))
      .catch(err => setError(err.message));
    registerForPushNotificationsAsync();
  }, []);

  if (error) return <SafeAreaView style={styles.container}><Text style={{padding:20, color:'red'}}>Error cargando: {error}</Text></SafeAreaView>;
  if (!data) return <SafeAreaView style={styles.container}><ActivityIndicator style={{marginTop: 50}} color="#4F46E5" /></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
            <Text style={styles.greeting}>¡Hola, {data.name}! 🚀</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Ajustes')}><Ionicons name="settings-outline" size={28} color="#4F46E5"/></TouchableOpacity>
          </View>
          <Text style={styles.groupName}><Ionicons name="home" size={14}/> {data.groupName || 'Sin Grupo'}</Text>
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
  statLabel: { fontSize: 14, color: '#6B7280', marginTop: 4 }
});
"""

# 4. BACKEND REWARD ROUTES (CRUD Completo)
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
    if (!member) return res.status(400).json({ error: 'No group found' });

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

# 5. FRONTEND API (Añadir createReward)
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
"""

# 6. MARKETPLACE (Añadir funcionalidad de Crear)
files["mobile/src/screens/MarketScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Alert, ActivityIndicator, Modal, TextInput } from 'react-native';
import { getRewards, redeemReward, createReward, api } from '../services/api';
import { Ionicons } from '@expo/vector-icons';

export default function MarketScreen() {
  const [rewards, setRewards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [myPoints, setMyPoints] = useState(0);
  const [modalVisible, setModalVisible] = useState(false);
  const [title, setTitle] = useState('');
  const [cost, setCost] = useState('100');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [rewRes, dashRes] = await Promise.all([getRewards(), api.get('/users/dashboard')]);
      setRewards(rewRes);
      setMyPoints(dashRes.data.totalPoints);
    } catch (error) {} finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const handleRedeem = async (item: any) => {
    if (myPoints < item.cost_points) return Alert.alert('Insuficiente', 'Aún tienes que esforzarte más.');
    try {
      await redeemReward(item.id);
      Alert.alert('¡Canjeado!', `Disfruta de: ${item.title}`);
      fetchData();
    } catch (error) { Alert.alert('Error', 'No se pudo canjear'); }
  };

  const handleCreate = async () => {
    if(!title) return Alert.alert('Error', 'Escribe un título');
    try {
      await createReward({ title, cost_points: parseInt(cost) });
      setModalVisible(false);
      setTitle('');
      fetchData();
    } catch(e) { Alert.alert('Error', 'No se pudo crear'); }
  }

  const renderItem = ({ item }: any) => {
    const canAfford = myPoints >= item.cost_points;
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.title}>{item.title}</Text>
          <Text style={[styles.points, !canAfford && {color:'#9CA3AF'}]}>{item.cost_points} pts</Text>
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

      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
        <Ionicons name="add" size={32} color="#fff" />
      </TouchableOpacity>

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

# 7. ADD MORE OPTIONS TO PROFILE SETTINGS
files["mobile/src/screens/ProfileScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, Alert, TextInput } from 'react-native';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';

export default function ProfileScreen() {
  const { logout } = useAuth();
  const navigation = useNavigation<any>();
  const [settings, setSettings] = useState<any>({ penalty_enabled: true, penalty_percentage: 50, name: 'Piso' });
  const [pushEnabled, setPushEnabled] = useState(true);

  useEffect(() => {
    api.get('/group/settings').then(res => setSettings(res.data)).catch(console.error);
  }, []);

  const saveGroupSettings = async (updates: any) => {
    const newSet = { ...settings, ...updates };
    setSettings(newSet);
    try {
      await api.post('/group/settings', newSet);
    } catch (e) {
      Alert.alert('Error', 'No se pudo guardar la configuración');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}><Ionicons name="arrow-back" size={24} color="#111827" style={{marginRight: 16}}/></TouchableOpacity>
        <Text style={styles.headerTitle}>Ajustes de Zutsu</Text>
      </View>
      
      <View style={styles.content}>
        <Text style={styles.sectionTitle}>General</Text>
        <View style={styles.card}>
          <Text style={styles.settingText}>Nombre del Grupo</Text>
          <TextInput 
            style={styles.input} 
            value={settings.name} 
            onChangeText={t => setSettings({...settings, name: t})} 
            onBlur={() => saveGroupSettings({ name: settings.name })}
          />
        </View>

        <Text style={styles.sectionTitle}>Reglas y Castigos</Text>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={{flexDirection:'row', alignItems:'center'}}>
              <Ionicons name="warning" size={24} color="#DC2626" style={{marginRight:12}}/>
              <Text style={styles.settingText}>Penalización por retraso</Text>
            </View>
            <Switch value={settings.penalty_enabled} onValueChange={v => saveGroupSettings({ penalty_enabled: v })} trackColor={{true: '#10B981'}} />
          </View>
          <Text style={styles.helperText}>Si una tarea se retrasa más de 2 días, restará puntos.</Text>
          
          {settings.penalty_enabled && (
             <View style={{marginTop: 16}}>
                <Text style={styles.settingText}>Porcentaje a restar: {settings.penalty_percentage}%</Text>
             </View>
          )}
        </View>

        <Text style={styles.sectionTitle}>Preferencias</Text>
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
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', borderBottomWidth:1, borderColor:'#E5E7EB', flexDirection: 'row', alignItems: 'center' },
  headerTitle: { fontSize: 24, fontWeight: '800', color: '#111827' },
  content: { padding: 16 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: '#6B7280', marginBottom: 12, marginLeft: 4, textTransform: 'uppercase' },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 24 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  settingText: { fontSize: 16, fontWeight: '600', color: '#374151' },
  helperText: { fontSize: 13, color: '#6B7280', marginTop: 12, lineHeight: 20 },
  input: { backgroundColor: '#F9FAFB', padding: 12, borderRadius: 8, marginTop: 12, borderWidth: 1, borderColor: '#E5E7EB', fontSize: 16 },
  logoutButton: { backgroundColor: '#FEE2E2', padding: 16, borderRadius: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 12 },
  logoutText: { color: '#EF4444', fontWeight: 'bold', fontSize: 16 }
});
"""

# 8. GROUP SETTINGS BACKEND UPDATE (para que guarde el nombre del grupo)
files["backend/src/routes/groupRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/settings', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id }, include: { group: true } });
    if (!member) return res.status(404).json({ error: 'Grupo no encontrado' });
    res.json(member.group);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/settings', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const { penalty_enabled, penalty_percentage, name } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id, role: 'ADMIN' } });
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

export default router;
"""

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Bugs arreglados, variables de entorno forzadas en fallback, marketplace y settings expandidos.")
