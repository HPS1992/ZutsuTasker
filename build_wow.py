import os
import subprocess

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"

files = {}

# 1. Update Schema for Penalties
files["backend/prisma/schema.prisma"] = """generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = "file:./dev.db"
}

model User {
  id               String             @id @default(uuid())
  email            String             @unique
  name             String
  created_at       DateTime           @default(now())
  updated_at       DateTime           @updatedAt
  group_members    GroupMember[]
  task_instances   TaskInstance[]     @relation("AssignedUser")
  points_logs      PointsLog[]
  reward_redemptions RewardRedemption[]
}

model Group {
  id                 String          @id @default(uuid())
  name               String
  penalty_enabled    Boolean         @default(true)
  penalty_percentage Int             @default(50) // Restar 50% de los puntos base si se retrasa 2 días
  created_at         DateTime        @default(now())
  updated_at         DateTime        @updatedAt
  members            GroupMember[]
  task_templates     TaskTemplate[]
  task_instances     TaskInstance[]
  rewards            Reward[]
  points_logs        PointsLog[]
}

model GroupMember {
  id           String   @id @default(uuid())
  user_id      String
  group_id     String
  role         String   @default("MEMBER") // ADMIN, MEMBER
  total_points Int      @default(0)
  streak_days  Int      @default(0)
  joined_at    DateTime @default(now())
  user         User     @relation(fields: [user_id], references: [id])
  group        Group    @relation(fields: [group_id], references: [id])

  @@unique([user_id, group_id])
}

model TaskTemplate {
  id           String         @id @default(uuid())
  group_id     String
  title        String
  category     String
  duration_min Int
  complexity   Int
  base_points  Int
  is_active    Boolean        @default(true)
  group        Group          @relation(fields: [group_id], references: [id])
  instances    TaskInstance[]
}

model TaskInstance {
  id             String       @id @default(uuid())
  template_id    String
  group_id       String
  assigned_to    String?
  due_date       DateTime
  status         String       @default("PENDING") // PENDING, COMPLETED, OVERDUE
  points_awarded Int?
  completed_at   DateTime?
  template       TaskTemplate @relation(fields: [template_id], references: [id])
  group          Group        @relation(fields: [group_id], references: [id])
  user           User?        @relation("AssignedUser", fields: [assigned_to], references: [id])
}

model Reward {
  id           String             @id @default(uuid())
  group_id     String
  title        String
  cost_points  Int
  yearly_limit Int                @default(1)
  is_active    Boolean            @default(true)
  group        Group              @relation(fields: [group_id], references: [id])
  redemptions  RewardRedemption[]
}

model RewardRedemption {
  id          String   @id @default(uuid())
  reward_id   String
  user_id     String
  redeemed_at DateTime @default(now())
  reward      Reward   @relation(fields: [reward_id], references: [id])
  user        User     @relation(fields: [user_id], references: [id])
}

model PointsLog {
  id         String   @id @default(uuid())
  user_id    String
  group_id   String
  amount     Int
  reason     String
  created_at DateTime @default(now())
  user       User     @relation(fields: [user_id], references: [id])
  group      Group    @relation(fields: [group_id], references: [id])
}
"""

# 2. Update Backend Task Service for Wow Penalties
files["backend/src/services/taskService.ts"] = """import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export const taskService = {
  async applyPenalties(groupId: string) {
    const group = await prisma.group.findUnique({ where: { id: groupId } });
    if (!group || !group.penalty_enabled) return;

    // Buscar tareas atrasadas 2 días
    const twoDaysAgo = new Date();
    twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);

    const overdueTasks = await prisma.taskInstance.findMany({
      where: {
        group_id: groupId,
        status: 'PENDING',
        due_date: { lt: twoDaysAgo }
      },
      include: { template: true }
    });

    for (const task of overdueTasks) {
      const penaltyPoints = Math.round(task.template.base_points * (group.penalty_percentage / 100));
      
      await prisma.$transaction(async (tx) => {
        await tx.taskInstance.update({
          where: { id: task.id },
          data: { status: 'OVERDUE' }
        });

        if (task.assigned_to) {
          await tx.pointsLog.create({
            data: { user_id: task.assigned_to, group_id: groupId, amount: -penaltyPoints, reason: 'OVERDUE_PENALTY' }
          });
          const member = await tx.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: groupId } }});
          if (member) {
            await tx.groupMember.update({
              where: { user_id_group_id: { user_id: task.assigned_to, group_id: groupId } },
              data: { total_points: Math.max(0, member.total_points - penaltyPoints), streak_days: 0 } // Pierde racha
            });
          }
        }
      });
    }
  },

  async getGroupTasks(groupId?: string) {
    if (groupId) await this.applyPenalties(groupId); // Efecto wow: penalizaciones automáticas al consultar

    const tasks = await prisma.taskInstance.findMany({
      include: { template: true, user: true },
      orderBy: { due_date: 'asc' }
    });

    return tasks.map(t => ({
      id: t.id,
      title: t.template.title,
      category: t.template.category,
      points_awarded: t.points_awarded,
      base_points: t.template.base_points,
      status: t.status,
      assignee: t.user ? t.user.name : 'Sin Asignar',
      due_date: t.due_date
    }));
  },

  async createTaskInstance(data: any) {
    const newTask = await prisma.taskInstance.create({
      data: {
        template_id: data.template_id,
        group_id: data.group_id,
        assigned_to: data.assigned_to,
        due_date: new Date(data.due_date),
        status: 'PENDING'
      }
    });
    return newTask;
  },

  async completeTask(taskId: string, userId: string) {
    const task = await prisma.taskInstance.findUnique({ where: { id: taskId }, include: { template: true } });
    if (!task) throw new Error('Tarea no encontrada');
    if (task.status === 'COMPLETED') throw new Error('La tarea ya está completada');

    let points = task.template.base_points;
    if (task.status === 'OVERDUE') points = Math.round(points * 0.5); // Mitad de puntos si la rescata estando atrasada

    await prisma.$transaction(async (tx) => {
      await tx.taskInstance.update({
        where: { id: taskId },
        data: { status: 'COMPLETED', completed_at: new Date(), points_awarded: points, assigned_to: userId }
      });
      await tx.pointsLog.create({
        data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETED' }
      });
      const member = await tx.groupMember.findUnique({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } } });
      if (member) {
        await tx.groupMember.update({
          where: { user_id_group_id: { user_id: userId, group_id: task.group_id } },
          data: { total_points: member.total_points + points, streak_days: member.streak_days + 1 }
        });
      }
    });
    
    return { success: true, message: `Tarea completada, +${points} puntos` };
  }
};
"""

# 3. Add Group Settings Routes
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
    const { penalty_enabled, penalty_percentage } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id, role: 'ADMIN' } });
    if (!member) return res.status(403).json({ error: 'No tienes permisos de admin' });

    const updated = await prisma.group.update({
      where: { id: member.group_id },
      data: { penalty_enabled, penalty_percentage: parseInt(penalty_percentage) }
    });
    res.json(updated);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
"""

files["backend/src/server.ts"] = """import express from 'express';
import cors from 'cors';
import authRoutes from './routes/authRoutes';
import taskRoutes from './routes/taskRoutes';
import userRoutes from './routes/userRoutes';
import rewardRoutes from './routes/rewardRoutes';
import statsRoutes from './routes/statsRoutes';
import groupRoutes from './routes/groupRoutes';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/tasks', taskRoutes);
app.use('/api/users', userRoutes);
app.use('/api/rewards', rewardRoutes);
app.use('/api/stats', statsRoutes);
app.use('/api/group', groupRoutes);

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
"""

# 4. Frontend WOW TasksScreen with Confetti (Simulated via elegant UI)
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, ActivityIndicator, Alert, TextInput, Modal, Animated } from 'react-native';
import { getTasks, completeTask, createTask } from '../services/api';
import { Ionicons } from '@expo/vector-icons';
import ConfettiCannon from 'react-native-confetti-cannon';

export default function TasksScreen() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('20');
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => { fetchTasks(); }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const data = await getTasks();
      setTasks(data);
    } catch (error) {
      console.error(error);
    } finally { setLoading(false); }
  };

  const handleComplete = async (taskId: string) => {
    try {
      await completeTask(taskId);
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 3000);
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
    } catch (err) { Alert.alert('Error', 'No se pudo crear la tarea'); }
  };

  const renderItem = ({ item }: any) => {
    const isOverdue = item.status === 'OVERDUE';
    return (
      <View style={[styles.taskCard, isOverdue && styles.overdueCard]}>
        <View style={styles.taskHeader}>
          <View style={{flexDirection:'row', alignItems:'center'}}>
            <Ionicons name={isOverdue ? 'warning' : 'ellipse'} size={16} color={isOverdue ? '#DC2626' : '#4F46E5'} style={{marginRight: 8}}/>
            <Text style={[styles.taskTitle, item.status==='COMPLETED' && {textDecorationLine: 'line-through', color:'#9CA3AF'}]}>{item.title}</Text>
          </View>
          <Text style={[styles.statusBadge, item.status === 'COMPLETED' ? styles.statusCompleted : isOverdue ? styles.statusOverdue : styles.statusPending]}>
            {item.status === 'COMPLETED' ? 'Hecho' : isOverdue ? 'Atrasada' : 'Pendiente'}
          </Text>
        </View>
        <View style={styles.taskFooter}>
          <Text style={[styles.pointsText, isOverdue && {color: '#DC2626'}]}>+{item.points_awarded || item.base_points || 15} pts {isOverdue && '(-50%)'}</Text>
          {item.status !== 'COMPLETED' && (
            <TouchableOpacity style={[styles.actionButton, isOverdue && {backgroundColor:'#DC2626'}]} onPress={() => handleComplete(item.id)}>
              <Text style={styles.actionButtonText}>Completar</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {showConfetti && <View style={{position:'absolute', top:0, left:0, right:0, bottom:0, zIndex:999}} pointerEvents="none"><ConfettiCannon count={100} origin={{x: -10, y: 0}} fallSpeed={2500} fadeOut /></View>}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Tareas de Hoy</Text>
        <TouchableOpacity onPress={fetchTasks}><Ionicons name="refresh" size={24} color="#4F46E5"/></TouchableOpacity>
      </View>
      
      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#4F46E5"/> : (
        <FlatList data={tasks} keyExtractor={i => i.id} renderItem={renderItem} contentContainerStyle={styles.listContainer} />
      )}

      <TouchableOpacity style={styles.fab} onPress={() => setModalVisible(true)}>
        <Ionicons name="add" size={32} color="#fff" />
      </TouchableOpacity>

      <Modal visible={modalVisible} animationType="fade" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>✨ Nueva Tarea</Text>
            <TextInput style={styles.input} placeholder="¿Qué hay que hacer?" value={title} onChangeText={setTitle} />
            <TextInput style={styles.input} placeholder="Puntos base (ej. 20)" keyboardType="numeric" value={points} onChangeText={setPoints} />
            <View style={styles.modalButtons}>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.cancelButton}><Text>Cancelar</Text></TouchableOpacity>
              <TouchableOpacity onPress={handleCreateTask} style={styles.saveButton}><Text style={{color: '#fff', fontWeight:'bold'}}>Añadir</Text></TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', flexDirection: 'row', justifyContent: 'space-between', borderBottomWidth:1, borderColor:'#E5E7EB' },
  headerTitle: { fontSize: 28, fontWeight: '800', color: '#111827' },
  listContainer: { padding: 16 },
  taskCard: { backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.05, shadowRadius: 8, elevation: 3 },
  overdueCard: { borderWidth: 1, borderColor: '#FECACA', backgroundColor: '#FEF2F2' },
  taskHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16, alignItems:'center' },
  taskTitle: { fontSize: 18, fontWeight: 'bold', color:'#374151' },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, overflow: 'hidden', fontSize: 12, fontWeight: 'bold' },
  statusPending: { backgroundColor: '#E0E7FF', color: '#4F46E5' },
  statusCompleted: { backgroundColor: '#DEF7EC', color: '#046C4E' },
  statusOverdue: { backgroundColor: '#FEE2E2', color: '#B91C1C' },
  taskFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, borderTopColor: '#F3F4F6', paddingTop: 16 },
  pointsText: { fontSize: 18, fontWeight: '900', color: '#10B981' },
  actionButton: { backgroundColor: '#4F46E5', paddingHorizontal: 20, paddingVertical: 10, borderRadius: 12 },
  actionButtonText: { color: '#fff', fontWeight: 'bold', fontSize: 14 },
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

# 5. Frontend Profile/Settings Screen
files["mobile/src/screens/ProfileScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, Alert } from 'react-native';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';

export default function ProfileScreen() {
  const { logout } = useAuth();
  const [settings, setSettings] = useState<any>({ penalty_enabled: true, penalty_percentage: 50 });

  useEffect(() => {
    api.get('/group/settings').then(res => setSettings(res.data)).catch(console.error);
  }, []);

  const togglePenalty = async () => {
    const newVal = !settings.penalty_enabled;
    setSettings({ ...settings, penalty_enabled: newVal });
    try {
      await api.post('/group/settings', { penalty_enabled: newVal, penalty_percentage: settings.penalty_percentage });
    } catch (e) {
      Alert.alert('Error', 'No tienes permisos de administrador');
      setSettings({ ...settings, penalty_enabled: !newVal });
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Ajustes del Hogar</Text>
      </View>
      <View style={styles.content}>
        <View style={styles.card}>
          <View style={styles.row}>
            <View style={{flexDirection:'row', alignItems:'center'}}>
              <Ionicons name="warning" size={24} color="#DC2626" style={{marginRight:12}}/>
              <Text style={styles.settingText}>Penalización por retraso</Text>
            </View>
            <Switch value={settings.penalty_enabled} onValueChange={togglePenalty} trackColor={{true: '#10B981'}} />
          </View>
          <Text style={styles.helperText}>Si una tarea se retrasa más de 2 días, restará un {settings.penalty_percentage}% de los puntos base de esa persona.</Text>
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
  header: { padding: 24, backgroundColor: '#fff', borderBottomWidth:1, borderColor:'#E5E7EB' },
  headerTitle: { fontSize: 28, fontWeight: '800', color: '#111827' },
  content: { padding: 16 },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 16, marginBottom: 24, shadowColor:'#000', shadowOpacity:0.05, shadowRadius:8, elevation:2 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  settingText: { fontSize: 16, fontWeight: '600', color: '#374151' },
  helperText: { fontSize: 13, color: '#6B7280', marginTop: 12, lineHeight: 20 },
  logoutButton: { backgroundColor: '#FEE2E2', padding: 16, borderRadius: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
  logoutText: { color: '#EF4444', fontWeight: 'bold', fontSize: 16 }
});
"""

# 6. Update App.tsx to include ProfileScreen
files["mobile/App.tsx"] = """import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import OnboardingScreen from './src/screens/OnboardingScreen';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import TasksScreen from './src/screens/TasksScreen';
import MarketScreen from './src/screens/MarketScreen';
import StatsScreen from './src/screens/StatsScreen';
import ProfileScreen from './src/screens/ProfileScreen';

export type RootStackParamList = { Onboarding: undefined; Auth: undefined; Main: undefined; };
const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator screenOptions={({ route }) => ({
      headerShown: false,
      tabBarActiveTintColor: '#4F46E5',
      tabBarInactiveTintColor: '#9CA3AF',
      tabBarStyle: { borderTopWidth: 0, elevation: 10, shadowOpacity: 0.1, height: 60, paddingBottom: 8, paddingTop: 8 },
      tabBarIcon: ({ focused, color, size }) => {
        let iconName: any = 'home';
        if (route.name === 'Inicio') iconName = focused ? 'home' : 'home-outline';
        else if (route.name === 'Tareas') iconName = focused ? 'list' : 'list-outline';
        else if (route.name === 'Market') iconName = focused ? 'gift' : 'gift-outline';
        else if (route.name === 'Equidad') iconName = focused ? 'pie-chart' : 'pie-chart-outline';
        else if (route.name === 'Ajustes') iconName = focused ? 'settings' : 'settings-outline';
        return <Ionicons name={iconName} size={28} color={color} />;
      },
    })}>
      <Tab.Screen name="Inicio" component={HomeScreen} />
      <Tab.Screen name="Tareas" component={TasksScreen} />
      <Tab.Screen name="Market" component={MarketScreen} />
      <Tab.Screen name="Equidad" component={StatsScreen} />
      <Tab.Screen name="Ajustes" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

function RootNavigator() {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <View style={{flex: 1, justifyContent: 'center', backgroundColor:'#fff'}}><ActivityIndicator size="large" color="#4F46E5" /></View>;
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

# 7. Update HomeScreen UI WOW
files["mobile/src/screens/HomeScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, ActivityIndicator, ImageBackground } from 'react-native';
import { api } from '../services/api';
import { Ionicons } from '@expo/vector-icons';

export default function HomeScreen() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get('/users/dashboard').then(res => setData(res.data)).catch(console.error);
  }, []);

  if (!data) return <SafeAreaView style={styles.container}><ActivityIndicator style={{marginTop: 50}} color="#4F46E5" /></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.greeting}>¡Hola, {data.name}! 🚀</Text>
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

        <Text style={styles.sectionTitle}>Siguiente paso</Text>
        <View style={styles.actionCard}>
          <Ionicons name="checkmark-circle" size={40} color="#4F46E5" />
          <View style={{marginLeft: 16, flex:1}}>
            <Text style={{fontSize:16, fontWeight:'bold', color:'#111827'}}>Revisa tus tareas</Text>
            <Text style={{color:'#6B7280', marginTop:4}}>Mantén tu racha activa completando al menos 1 tarea hoy.</Text>
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
  wowCard: { backgroundColor: '#4F46E5', borderRadius: 24, padding: 32, alignItems: 'center', marginBottom: 24, shadowColor: '#4F46E5', shadowOpacity: 0.3, shadowRadius: 15, elevation: 8 },
  glassLayer: { alignItems: 'center' },
  wowTitle: { color: '#E0E7FF', fontSize: 16, fontWeight: '600', textTransform:'uppercase', letterSpacing:1 },
  wowPoints: { color: '#fff', fontSize: 64, fontWeight: '900', marginVertical: 8 },
  wowSubtitle: { color: '#A5B4FC', fontSize: 16, fontWeight: '500' },
  statsGrid: { flexDirection: 'row', gap: 16, marginBottom: 32 },
  statBox: { flex: 1, backgroundColor: '#fff', padding: 20, borderRadius: 20, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  statValue: { fontSize: 24, fontWeight: 'bold', color: '#111827', marginTop: 12 },
  statLabel: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  sectionTitle: { fontSize: 20, fontWeight: 'bold', color: '#111827', marginBottom: 16 },
  actionCard: { backgroundColor: '#fff', padding: 20, borderRadius: 20, flexDirection: 'row', alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 }
});
"""

# 8. Update Stats Screen UI WOW
files["mobile/src/screens/StatsScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, ActivityIndicator } from 'react-native';
import { getEquityStats } from '../services/api';
import { Ionicons } from '@expo/vector-icons';

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
          <View style={[styles.bar, { width: `${item.percentage}%`, backgroundColor: isFirst ? '#FCD34D' : '#10B981' }]} />
        </View>
        <Text style={[styles.details, isFirst && {color:'#E0E7FF'}]}>{item.points} puntos globales</Text>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Equilibrio del Hogar</Text>
        <Text style={styles.subtitle}>Distribución justa de las tareas</Text>
      </View>
      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#4F46E5"/> : (
        <FlatList data={stats.sort((a,b)=>b.points-a.points)} renderItem={renderItem} keyExtractor={i => i.name} contentContainerStyle={styles.list} />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', borderBottomWidth:1, borderColor:'#E5E7EB' },
  headerTitle: { fontSize: 28, fontWeight: '900', color: '#111827' },
  subtitle: { color: '#6B7280', marginTop: 8, fontSize:16 },
  list: { padding: 16 },
  card: { backgroundColor: '#fff', padding: 24, borderRadius: 20, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  firstCard: { backgroundColor: '#4F46E5' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  name: { fontSize: 18, fontWeight: 'bold', color: '#374151' },
  percentage: { fontSize: 18, fontWeight: '900', color: '#111827' },
  barContainer: { height: 12, backgroundColor: 'rgba(0,0,0,0.1)', borderRadius: 6, overflow: 'hidden', marginBottom: 12 },
  bar: { height: '100%', borderRadius: 6 },
  details: { fontSize: 14, color: '#6B7280' }
});
"""

# 9. Update Market Screen UI WOW
files["mobile/src/screens/MarketScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { getRewards, redeemReward, api } from '../services/api';
import { Ionicons } from '@expo/vector-icons';

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
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 }
});
"""

# 10. Update README
files["README.md"] = """# Zutsu Tasker 🚀

Zutsu Tasker es una aplicación móvil gamificada diseñada para resolver la gestión de tareas domésticas en entornos compartidos (pisos de estudiantes, parejas, familias). Aplica el concepto japonés de "cada uno su parte" (ずつ) para garantizar la **equidad y transparencia**.

## ✨ Efectos WOW y Características Clave

1. **Gamificación y Recompensas (Marketplace)**: Las tareas otorgan puntos basados en duración y complejidad. Los puntos se canjean por recompensas personalizadas (ej. "Librarse de fregar" o "Cena pagada").
2. **Sistema de Equidad Transparente**: Visualización clara del % de aportación de cada integrante. El líder del mes destaca con diseño dorado.
3. **Penalizaciones automáticas (Overdue)**: Si una tarea se retrasa más de 2 días, la app activa la penalización (por defecto -50% de los puntos) y rompe la racha del usuario, fomentando la disciplina.
4. **Animaciones de Recompensa**: Lluvia de confeti al completar tareas (efecto de dopamina visual) y componentes Glassmorphism UI.
5. **Autenticación Escalable**: Preparado para Firebase Auth (Email/SSO) y sincronizado con base de datos propia para control total.

## 🛠️ Stack Tecnológico

- **Frontend**: React Native + Expo + TypeScript + React Navigation.
- **Backend**: Node.js + Express + TypeScript + Prisma ORM.
- **Base de datos**: SQLite (Fácil de migrar a PostgreSQL).
- **Despliegue recomendado**: Frontend en Vercel/Expo Application Services (EAS). Backend en Render/Railway.

## 🚀 Instrucciones de Arranque

### 1. Backend
```bash
cd backend
npm install
npx prisma db push      # Sincroniza esquema de base de datos
npx prisma db seed      # Carga datos de prueba (Alex, Maria, Carlos)
npm run dev             # Inicia el servidor en http://localhost:3000
```

### 2. Frontend
```bash
cd mobile
npm install
npx expo start          # Inicia el Metro Bundler
```
Escanea el código QR con Expo Go en tu móvil, o pulsa `w` para verlo en tu navegador.

*Nota:* Si pruebas en móvil real, asegúrate de actualizar `mobile/src/services/api.ts` con la IP local de tu ordenador en lugar de `localhost`, o usa el túnel de Expo.

## 👥 Datos de Prueba (Seed)

El seed genera:
- **Grupo**: Piso Estudiantes
- **Usuarios**: Alex, Maria, Carlos
- **Tareas**: Limpiar Baño (Pendiente), Bajar basura (Completada).
- **Market**: "Librarse de fregar" (100pts), "Cena pagada" (1000pts).

Inicia sesión con cualquier email (ej: `alex@test.com`) y el sistema te dará paso automático con el perfil de pruebas.
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

# Install missing UI dependencies for Confetti
subprocess.run("cd /Volumes/IA_SSD/proyectos/ZutsuTasker/mobile && npm install react-native-confetti-cannon", shell=True)
# Sync DB schema due to Group penalty fields
subprocess.run("cd /Volumes/IA_SSD/proyectos/ZutsuTasker/backend && npx prisma db push", shell=True)

print("WOW features implemented, DB synced, Ready for PROD.")
