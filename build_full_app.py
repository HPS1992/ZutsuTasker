import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# --- BACKEND REWARDS ---
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

# --- BACKEND STATS ---
files["backend/src/routes/statsRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/equity', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    const members = await prisma.groupMember.findMany({
      where: { group_id: member.group_id },
      include: { user: true }
    });

    const totalGroupPoints = members.reduce((acc, m) => acc + m.total_points, 0);

    const stats = members.map(m => ({
      name: m.user.name,
      points: m.total_points,
      percentage: totalGroupPoints === 0 ? 0 : Math.round((m.total_points / totalGroupPoints) * 100)
    }));

    res.json(stats);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
"""

# --- BACKEND SERVER UPDATE ---
files["backend/src/server.ts"] = """import express from 'express';
import cors from 'cors';
import authRoutes from './routes/authRoutes';
import taskRoutes from './routes/taskRoutes';
import userRoutes from './routes/userRoutes';
import rewardRoutes from './routes/rewardRoutes';
import statsRoutes from './routes/statsRoutes';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/tasks', taskRoutes);
app.use('/api/users', userRoutes);
app.use('/api/rewards', rewardRoutes);
app.use('/api/stats', statsRoutes);

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
"""

# --- BACKEND TASK ROUTES UPDATE ---
files["backend/src/routes/taskRoutes.ts"] = """import { Router } from 'express';
import { listTasks, createTask, completeTask } from '../controllers/taskController';
import { requireAuth } from '../middleware/authMiddleware';

const router = Router();

router.get('/', requireAuth, listTasks);
router.post('/', requireAuth, createTask);
router.post('/:id/complete', requireAuth, completeTask);

export default router;
"""

files["backend/src/controllers/taskController.ts"] = """import { Request, Response } from 'express';
import { taskService } from '../services/taskService';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export const listTasks = async (req: Request, res: Response) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });
    
    const tasks = await taskService.getGroupTasks(member.group_id);
    res.status(200).json(tasks);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
};

export const createTask = async (req: Request, res: Response) => {
  try {
    const user = req.user;
    const { title, category, points, due_date } = req.body;
    
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    // En vez de usar un template real, creamos uno al vuelo (simplificación para MVP)
    const template = await prisma.taskTemplate.create({
      data: {
        group_id: member.group_id,
        title,
        category,
        duration_min: 15,
        complexity: 2,
        base_points: parseInt(points) || 20
      }
    });

    const newTask = await prisma.taskInstance.create({
      data: {
        template_id: template.id,
        group_id: member.group_id,
        due_date: due_date ? new Date(due_date) : new Date(),
        status: 'PENDING'
      }
    });

    res.status(201).json(newTask);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};

export const completeTask = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const user = req.user;
    const result = await taskService.completeTask(id, user.id);
    res.status(200).json(result);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};
"""


# --- FRONTEND API UPDATE ---
files["mobile/src/services/api.ts"] = """import axios from 'axios';

// Usar localhost para desarrollo web.
const API_URL = 'http://localhost:3000/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export const getTasks = async () => (await api.get(`/tasks`)).data;
export const createTask = async (data: any) => (await api.post(`/tasks`, data)).data;
export const completeTask = async (taskId: string) => (await api.post(`/tasks/${taskId}/complete`)).data;
export const getRewards = async () => (await api.get(`/rewards`)).data;
export const redeemReward = async (id: string) => (await api.post(`/rewards/${id}/redeem`)).data;
export const getEquityStats = async () => (await api.get(`/stats/equity`)).data;
"""


# --- FRONTEND MARKET SCREEN ---
files["mobile/src/screens/MarketScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { getRewards, redeemReward, api } from '../services/api';

export default function MarketScreen() {
  const [rewards, setRewards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [myPoints, setMyPoints] = useState(0);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [rewRes, dashRes] = await Promise.all([getRewards(), api.get('/users/dashboard')]);
      setRewards(rewRes);
      setMyPoints(dashRes.data.totalPoints);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleRedeem = async (item: any) => {
    if (myPoints < item.cost_points) {
      return Alert.alert('Puntos insuficientes', 'No tienes suficientes puntos para esta recompensa.');
    }
    try {
      await redeemReward(item.id);
      Alert.alert('¡Canjeado!', `Has canjeado: ${item.title}`);
      fetchData(); // Refrescar puntos
    } catch (error) {
      Alert.alert('Error', 'No se pudo canjear la recompensa.');
    }
  };

  const renderItem = ({ item }: any) => (
    <View style={styles.card}>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.points}>{item.cost_points} pts</Text>
      <TouchableOpacity 
        style={[styles.button, myPoints < item.cost_points && styles.buttonDisabled]} 
        onPress={() => handleRedeem(item)}
      >
        <Text style={styles.buttonText}>Canjear</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Market</Text>
        <Text style={styles.myPoints}>Mis Puntos: {myPoints}</Text>
      </View>
      {loading ? <ActivityIndicator style={{marginTop: 50}} /> : (
        <FlatList data={rewards} renderItem={renderItem} keyExtractor={i => i.id} contentContainerStyle={styles.list} />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  header: { padding: 20, backgroundColor: '#fff', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { fontSize: 24, fontWeight: 'bold' },
  myPoints: { fontSize: 16, fontWeight: 'bold', color: '#4F46E5' },
  list: { padding: 16 },
  card: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 12, flexDirection: 'row', alignItems: 'center' },
  title: { flex: 1, fontSize: 16, fontWeight: 'bold' },
  points: { fontSize: 16, color: '#10B981', fontWeight: 'bold', marginRight: 16 },
  button: { backgroundColor: '#4F46E5', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  buttonDisabled: { backgroundColor: '#9CA3AF' },
  buttonText: { color: '#fff', fontWeight: 'bold' }
});
"""

# --- FRONTEND STATS SCREEN ---
files["mobile/src/screens/StatsScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, ActivityIndicator } from 'react-native';
import { getEquityStats } from '../services/api';

export default function StatsScreen() {
  const [stats, setStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEquityStats().then(setStats).finally(() => setLoading(false));
  }, []);

  const renderItem = ({ item }: any) => (
    <View style={styles.card}>
      <Text style={styles.name}>{item.name}</Text>
      <View style={styles.barContainer}>
        <View style={[styles.bar, { width: `${item.percentage}%` }]} />
      </View>
      <Text style={styles.details}>{item.points} pts ({item.percentage}%)</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Equidad del Grupo</Text>
        <Text style={styles.subtitle}>Distribución del trabajo en casa</Text>
      </View>
      {loading ? <ActivityIndicator style={{marginTop: 50}} /> : (
        <FlatList data={stats} renderItem={renderItem} keyExtractor={i => i.name} contentContainerStyle={styles.list} />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  header: { padding: 20, backgroundColor: '#fff' },
  headerTitle: { fontSize: 24, fontWeight: 'bold' },
  subtitle: { color: '#6B7280', marginTop: 4 },
  list: { padding: 16 },
  card: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 12 },
  name: { fontSize: 16, fontWeight: 'bold', marginBottom: 8 },
  barContainer: { height: 10, backgroundColor: '#E5E7EB', borderRadius: 5, overflow: 'hidden', marginBottom: 8 },
  bar: { height: '100%', backgroundColor: '#10B981' },
  details: { fontSize: 14, color: '#4B5563', textAlign: 'right' }
});
"""

# --- FRONTEND APP NAVIGATION UPDATE ---
files["mobile/App.tsx"] = """import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import OnboardingScreen from './src/screens/OnboardingScreen';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import TasksScreen from './src/screens/TasksScreen';
import MarketScreen from './src/screens/MarketScreen';
import StatsScreen from './src/screens/StatsScreen';

export type RootStackParamList = { Onboarding: undefined; Auth: undefined; Main: undefined; };
const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false, tabBarActiveTintColor: '#4F46E5' }}>
      <Tab.Screen name="Home" component={HomeScreen} options={{ tabBarLabel: 'Inicio' }} />
      <Tab.Screen name="Tareas" component={TasksScreen} />
      <Tab.Screen name="Market" component={MarketScreen} />
      <Tab.Screen name="Equidad" component={StatsScreen} />
    </Tab.Navigator>
  );
}

function RootNavigator() {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <View style={{flex: 1, justifyContent: 'center'}}><ActivityIndicator size="large" color="#4F46E5" /></View>;
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!user ? (
        <Stack.Screen name="Auth" component={LoginScreen} />
      ) : (
        <Stack.Screen name="Main" component={MainTabs} />
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NavigationContainer>
          <RootNavigator />
        </NavigationContainer>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
"""

# --- FRONTEND CREATE TASK (Replaced in TasksScreen for simplicity) ---
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, ActivityIndicator, Alert, TextInput, Modal } from 'react-native';
import { getTasks, completeTask, createTask } from '../services/api';

export default function TasksScreen() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  
  // Formulario nueva tarea
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('20');

  useEffect(() => { fetchTasks(); }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const data = await getTasks();
      setTasks(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (taskId: string) => {
    try {
      await completeTask(taskId);
      fetchTasks();
    } catch (error) {
      Alert.alert('Error', 'No se pudo completar');
    }
  };

  const handleCreateTask = async () => {
    if (!title) return Alert.alert('Error', 'Ponle nombre a la tarea');
    try {
      await createTask({ title, category: 'General', points: parseInt(points) });
      setModalVisible(false);
      setTitle('');
      fetchTasks();
    } catch (err) {
      Alert.alert('Error', 'No se pudo crear la tarea');
    }
  };

  const renderItem = ({ item }: any) => (
    <View style={styles.taskCard}>
      <View style={styles.taskHeader}>
        <Text style={styles.taskTitle}>{item.title}</Text>
        <Text style={[styles.statusBadge, item.status === 'COMPLETED' ? styles.statusCompleted : styles.statusPending]}>
          {item.status === 'COMPLETED' ? 'Hecho' : 'Pendiente'}
        </Text>
      </View>
      <View style={styles.taskFooter}>
        <Text style={styles.pointsText}>+{item.points_awarded || item.base_points || 15} pts</Text>
        {item.status === 'PENDING' && (
          <TouchableOpacity style={styles.actionButton} onPress={() => handleComplete(item.id)}>
            <Text style={styles.actionButtonText}>Completar</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Tareas</Text>
        <TouchableOpacity onPress={fetchTasks}><Text style={styles.refreshText}>↻ Actualizar</Text></TouchableOpacity>
      </View>
      
      {loading ? <ActivityIndicator style={{marginTop: 50}} /> : (
        <FlatList data={tasks} keyExtractor={i => i.id} renderItem={renderItem} contentContainerStyle={styles.listContainer} />
      )}

      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>

      <Modal visible={modalVisible} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Nueva Tarea</Text>
            <TextInput style={styles.input} placeholder="¿Qué hay que hacer?" value={title} onChangeText={setTitle} />
            <TextInput style={styles.input} placeholder="Puntos (ej. 20)" keyboardType="numeric" value={points} onChangeText={setPoints} />
            <View style={styles.modalButtons}>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}>
                <Text>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={handleCreateTask} style={styles.saveButton}>
                <Text style={{color: '#fff', fontWeight:'bold'}}>Crear</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  header: { padding: 20, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#F3F4F6', flexDirection: 'row', justifyContent: 'space-between' },
  headerTitle: { fontSize: 24, fontWeight: 'bold' },
  refreshText: { color: '#4F46E5', fontWeight: 'bold' },
  listContainer: { padding: 16 },
  taskCard: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 12 },
  taskHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  taskTitle: { fontSize: 18, fontWeight: 'bold' },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6, overflow: 'hidden', fontSize: 12, fontWeight: 'bold' },
  statusPending: { backgroundColor: '#FEF3C7', color: '#92400E' },
  statusCompleted: { backgroundColor: '#DEF7EC', color: '#046C4E' },
  taskFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, borderTopColor: '#F3F4F6', paddingTop: 12 },
  pointsText: { fontSize: 16, fontWeight: 'bold', color: '#4F46E5' },
  actionButton: { backgroundColor: '#10B981', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  actionButtonText: { color: '#fff', fontWeight: 'bold' },
  fab: { position: 'absolute', bottom: 24, right: 24, width: 60, height: 60, borderRadius: 30, backgroundColor: '#4F46E5', justifyContent: 'center', alignItems: 'center' },
  fabText: { fontSize: 32, color: '#fff', marginTop: -2 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: '#fff', padding: 20, borderRadius: 16 },
  modalTitle: { fontSize: 20, fontWeight: 'bold', marginBottom: 16 },
  input: { backgroundColor: '#F3F4F6', padding: 12, borderRadius: 8, marginBottom: 12 },
  modalButtons: { flexDirection: 'row', justifyContent: 'flex-end', gap: 12, marginTop: 10 },
  cancelButton: { padding: 12 },
  saveButton: { backgroundColor: '#4F46E5', padding: 12, borderRadius: 8 }
});
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Full project implemented!")
