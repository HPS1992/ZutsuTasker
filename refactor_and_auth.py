import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. ESTADO GLOBAL (Zustand)
os.makedirs(os.path.join(base_dir, "mobile/src/store"), exist_ok=True)
files["mobile/src/store/useTaskStore.ts"] = """import { create } from 'zustand';
import { getTasks, completeTask, createTask } from '../services/api';

interface TaskStore {
  tasks: any[];
  loading: boolean;
  fetchTasks: () => Promise<void>;
  completeTask: (taskId: string) => Promise<void>;
  addTask: (title: string, points: number) => Promise<void>;
}

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: [],
  loading: false,
  fetchTasks: async () => {
    set({ loading: true });
    try {
      const data = await getTasks();
      set({ tasks: data, loading: false });
    } catch (e) {
      set({ loading: false });
      throw e;
    }
  },
  completeTask: async (taskId: string) => {
    await completeTask(taskId);
    await get().fetchTasks(); // Refrescar tras completar
  },
  addTask: async (title: string, points: number) => {
    await createTask({ title, category: 'General', points });
    await get().fetchTasks(); // Refrescar tras añadir
  }
}));
"""

# 2. COMPONENTES REUTILIZABLES (Clean Code)
os.makedirs(os.path.join(base_dir, "mobile/src/components"), exist_ok=True)
files["mobile/src/components/TaskCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface TaskCardProps {
  item: any;
  onComplete: (id: string) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({ item, onComplete }) => {
  const isOverdue = item.status === 'OVERDUE';
  const isCompleted = item.status === 'COMPLETED';

  return (
    <View style={[styles.taskCard, isOverdue && styles.overdueCard]}>
      <View style={styles.taskHeader}>
        <View style={{flexDirection:'row', alignItems:'center'}}>
          <Ionicons name={isOverdue ? 'warning' : 'ellipse'} size={16} color={isOverdue ? '#DC2626' : '#4F46E5'} style={{marginRight: 8}}/>
          <Text style={[styles.taskTitle, isCompleted && {textDecorationLine: 'line-through', color:'#9CA3AF'}]}>{item.title}</Text>
        </View>
        <Text style={[styles.statusBadge, isCompleted ? styles.statusCompleted : isOverdue ? styles.statusOverdue : styles.statusPending]}>
          {isCompleted ? 'Hecho' : isOverdue ? 'Atrasada' : 'Pendiente'}
        </Text>
      </View>
      <View style={styles.taskFooter}>
        <Text style={[styles.pointsText, isOverdue && {color: '#DC2626'}]}>
          +{item.points_awarded || item.base_points || 15} pts {isOverdue && '(-50%)'}
        </Text>
        {!isCompleted && (
          <TouchableOpacity style={[styles.actionButton, isOverdue && {backgroundColor:'#DC2626'}]} onPress={() => onComplete(item.id)}>
            <Text style={styles.actionButtonText}>Completar</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
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
  actionButtonText: { color: '#fff', fontWeight: 'bold', fontSize: 14 }
});
"""

# 3. REFACTORIZACIÓN DE PANTALLA TAREAS (Usando Store y Componente)
files["mobile/src/screens/TasksScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, ActivityIndicator, Alert, TextInput, Modal } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import ConfettiCannon from 'react-native-confetti-cannon';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';

export default function TasksScreen() {
  const { tasks, loading, fetchTasks, completeTask, addTask } = useTaskStore();
  const [modalVisible, setModalVisible] = useState(false);
  const [title, setTitle] = useState('');
  const [points, setPoints] = useState('20');
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => { fetchTasks(); }, []);

  const handleComplete = async (taskId: string) => {
    try {
      await completeTask(taskId);
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 3000);
    } catch (error) {
      Alert.alert('Error', 'No se pudo completar');
    }
  };

  const handleCreateTask = async () => {
    if (!title) return Alert.alert('Error', 'Ponle nombre a la tarea');
    try {
      await addTask(title, parseInt(points));
      setModalVisible(false);
      setTitle('');
    } catch (err) { Alert.alert('Error', 'No se pudo crear la tarea'); }
  };

  return (
    <SafeAreaView style={styles.container}>
      {showConfetti && <View style={styles.confettiContainer} pointerEvents="none"><ConfettiCannon count={100} origin={{x: -10, y: 0}} fallSpeed={2500} fadeOut /></View>}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Tareas de Hoy</Text>
        <TouchableOpacity onPress={fetchTasks}><Ionicons name="refresh" size={24} color="#4F46E5"/></TouchableOpacity>
      </View>
      
      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#4F46E5"/> : (
        <FlatList data={tasks} keyExtractor={i => i.id} renderItem={({item}) => <TaskCard item={item} onComplete={handleComplete} />} contentContainerStyle={styles.listContainer} />
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
  confettiContainer: {position:'absolute', top:0, left:0, right:0, bottom:0, zIndex:999},
  header: { padding: 24, backgroundColor: '#fff', flexDirection: 'row', justifyContent: 'space-between', borderBottomWidth:1, borderColor:'#E5E7EB' },
  headerTitle: { fontSize: 28, fontWeight: '800', color: '#111827' },
  listContainer: { padding: 16 },
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

# 4. .ENV EN FRONTEND Y BACKEND PARA FIREBASE REAL
files["mobile/.env"] = """EXPO_PUBLIC_USE_MOCK_AUTH=true
# Rellena estos datos desde la consola de Firebase cuando pases a prod
EXPO_PUBLIC_FIREBASE_API_KEY=
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=
EXPO_PUBLIC_FIREBASE_PROJECT_ID=
EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET=
EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
EXPO_PUBLIC_FIREBASE_APP_ID=
"""

files["backend/.env"] = """PORT=3000
USE_MOCK_AUTH=true
# Ruta al JSON de tu Service Account de Firebase Admin
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-admin.json
"""

# 5. INTEGRACIÓN DE ENV EN FRONTEND Y PREPARACIÓN DE AUTH REAL
files["mobile/src/config/firebase.ts"] = """import { initializeApp } from 'firebase/app';
import { getAuth, initializeAuth, getReactNativePersistence, browserLocalPersistence } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const firebaseConfig = {
  apiKey: process.env.EXPO_PUBLIC_FIREBASE_API_KEY || "TU_API_KEY",
  authDomain: process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN || "zutsu-tasker.firebaseapp.com",
  projectId: process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID || "zutsu-tasker",
  storageBucket: process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET || "zutsu-tasker.appspot.com",
  messagingSenderId: process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "123456789",
  appId: process.env.EXPO_PUBLIC_FIREBASE_APP_ID || "1:123456789:web:abcdef"
};

const app = initializeApp(firebaseConfig);
export const auth = initializeAuth(app, {
  persistence: Platform.OS === 'web' ? browserLocalPersistence : getReactNativePersistence(AsyncStorage)
});
"""

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

  const useMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === 'true';

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

# 6. BACKEND FIREBASE ADMIN MIDDLEWARE PREP
files["backend/src/middleware/authMiddleware.ts"] = """import { Request, Response, NextFunction } from 'express';
import { PrismaClient } from '@prisma/client';
import * as admin from 'firebase-admin';
import dotenv from 'dotenv';
dotenv.config();

const prisma = new PrismaClient();
const useMockAuth = process.env.USE_MOCK_AUTH === 'true';

// Configuración perezosa de Firebase Admin por si el archivo no existe aún
let adminInitialized = false;
try {
  if (!useMockAuth && process.env.FIREBASE_SERVICE_ACCOUNT_PATH) {
    const serviceAccount = require('../../firebase-admin.json');
    admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
    adminInitialized = true;
  }
} catch (e) {
  console.warn("⚠️ No se pudo inicializar Firebase Admin. Asegúrate de tener firebase-admin.json");
}

declare global {
  namespace Express {
    interface Request {
      user?: any;
    }
  }
}

export const requireAuth = async (req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split('Bearer ')[1];
  if (!token) return res.status(401).json({ error: 'No token provided' });

  try {
    if (useMockAuth) {
      // MODO DESARROLLO SIN FIREBASE: Siempre asumimos que es el usuario de prueba
      const user = await prisma.user.findFirst({ where: { email: 'alex@test.com' }});
      if (!user) throw new Error('User not found in DB');
      req.user = user;
      return next();
    }

    // MODO PRODUCCIÓN: Validar token real con Firebase Admin
    if (!adminInitialized) throw new Error("Firebase admin not configured on server");
    
    const decodedToken = await admin.auth().verifyIdToken(token);
    // Buscar el usuario por su UID de Firebase o email (depende de tu tabla users)
    const user = await prisma.user.findUnique({ where: { email: decodedToken.email } });
    
    if (!user) return res.status(401).json({ error: 'Unregistered user' });
    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};
"""

files["backend/package.json"] = """{
  "name": "zutsu-backend",
  "version": "1.0.0",
  "scripts": {
    "dev": "tsx watch src/server.ts",
    "seed": "tsx prisma/seed.ts"
  },
  "dependencies": {
    "@prisma/client": "^6.19.3",
    "cors": "^2.8.5",
    "dotenv": "^16.4.5",
    "express": "^4.19.2",
    "firebase-admin": "^12.0.0"
  },
  "devDependencies": {
    "@types/cors": "^2.8.17",
    "@types/express": "^4.17.21",
    "@types/node": "^22.0.0",
    "prisma": "^6.19.3",
    "tsx": "^4.19.1",
    "typescript": "^5.0.0"
  },
  "prisma": {
    "seed": "tsx prisma/seed.ts"
  }
}
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Refactorización (Zustand + Clean Code) y configuración de Seguridad (Firebase + .env) implementados con éxito.")
