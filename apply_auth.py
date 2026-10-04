import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"

files = {}

# 1. Firebase config frontend
files["mobile/src/config/firebase.ts"] = """import { initializeApp } from 'firebase/app';
import { getAuth, initializeAuth, getReactNativePersistence } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Reemplaza con tus credenciales reales de Firebase luego
const firebaseConfig = {
  apiKey: "TU_API_KEY",
  authDomain: "zutsu-tasker.firebaseapp.com",
  projectId: "zutsu-tasker",
  storageBucket: "zutsu-tasker.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
};

const app = initializeApp(firebaseConfig);

// Persistence is important for React Native to keep user logged in
export const auth = initializeAuth(app, {
  persistence: getReactNativePersistence(AsyncStorage)
});
"""

# 2. AuthContext Frontend
os.makedirs(os.path.join(base_dir, "mobile/src/context"), exist_ok=True)
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

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (usr) => {
      setUser(usr);
      if (usr) {
        // Obtenemos token y lo inyectamos por defecto a Axios
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
    // Si da error "invalid-api-key" es porque falta poner config de firebase
    // En un MVP mock, si falla firebase lo bypasseamos. 
    // Para simplificar tu prueba inmediata:
    try {
      await signInWithEmailAndPassword(auth, e, p);
    } catch (err: any) {
      if (err.message.includes('API key')) {
        // Fake login for development without firebase keys
        setUser({ uid: 'u123', email: e } as User);
        api.defaults.headers.common['Authorization'] = `Bearer MOCK_TOKEN`;
      } else {
        throw err;
      }
    }
  };

  const register = async (e: string, p: string, name: string) => {
    try {
      const cred = await createUserWithEmailAndPassword(auth, e, p);
      const token = await cred.user.getIdToken();
      await api.post('/auth/register', { email: e, name, firebase_uid: cred.user.uid }, {
        headers: { Authorization: `Bearer ${token}` }
      });
    } catch (err: any) {
      if (err.message.includes('API key')) {
         setUser({ uid: 'u123', email: e } as User);
         api.defaults.headers.common['Authorization'] = `Bearer MOCK_TOKEN`;
      } else {
         throw err;
      }
    }
  };

  const logout = () => {
    setUser(null);
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

# 3. Update App.tsx
files["mobile/App.tsx"] = """import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ActivityIndicator, View } from 'react-native';

import OnboardingScreen from './src/screens/OnboardingScreen';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import TasksScreen from './src/screens/TasksScreen';

export type RootStackParamList = { Onboarding: undefined; Auth: undefined; Main: undefined; };
const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Tareas" component={TasksScreen} />
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
    <AuthProvider>
      <NavigationContainer>
        <RootNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}
"""

# 4. LoginScreen Update
files["mobile/src/screens/LoginScreen.tsx"] = """import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, SafeAreaView, Alert } from 'react-native';
import { useAuth } from '../context/AuthContext';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async () => {
    try {
      if (isRegistering) {
        if (!name) return Alert.alert('Error', 'El nombre es obligatorio');
        await register(email, password, name);
      } else {
        await login(email, password);
      }
    } catch (err: any) {
      Alert.alert('Error', err.message);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.formContainer}>
        <Text style={styles.header}>Zutsu Tasker</Text>
        <Text style={styles.subHeader}>{isRegistering ? 'Únete al equipo' : 'El equilibrio empieza en casa'}</Text>

        {isRegistering && (
          <TextInput style={styles.input} placeholder="Tu nombre" value={name} onChangeText={setName} />
        )}
        <TextInput style={styles.input} placeholder="Correo electrónico" autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} />
        <TextInput style={styles.input} placeholder="Contraseña" secureTextEntry value={password} onChangeText={setPassword} />

        <TouchableOpacity style={styles.primaryButton} onPress={handleSubmit}>
          <Text style={styles.primaryButtonText}>{isRegistering ? 'Crear Cuenta' : 'Iniciar Sesión'}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={() => setIsRegistering(!isRegistering)}>
          <Text style={styles.secondaryButtonText}>
            {isRegistering ? 'Ya tengo cuenta, iniciar sesión' : 'Crear una cuenta nueva'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  formContainer: { flex: 1, justifyContent: 'center', padding: 24 },
  header: { fontSize: 32, fontWeight: 'bold', color: '#1F2937', textAlign: 'center' },
  subHeader: { fontSize: 16, color: '#6B7280', textAlign: 'center', marginBottom: 40 },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 10, marginBottom: 16, fontSize: 16 },
  primaryButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 10, alignItems: 'center', marginTop: 8 },
  primaryButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  secondaryButton: { padding: 16, alignItems: 'center', marginTop: 8 },
  secondaryButtonText: { color: '#4F46E5', fontSize: 16, fontWeight: '600' },
});
"""

# 5. HomeScreen Update
files["mobile/src/screens/HomeScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function HomeScreen({ navigation }: any) {
  const { logout } = useAuth();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get('/users/dashboard')
       .then(res => setData(res.data))
       .catch(err => console.error('Error cargando dashboard', err));
  }, []);

  if (!data) return <SafeAreaView style={styles.container}><ActivityIndicator style={{marginTop: 50}} color="#4F46E5" /></SafeAreaView>;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Hola, {data.name} 👋</Text>
          <Text style={styles.groupName}>{data.groupName || 'Sin Grupo'}</Text>
        </View>

        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{data.totalPoints}</Text>
            <Text style={styles.statLabel}>Pts Totales</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{data.totalPoints || 0}</Text>
            <Text style={styles.statLabel}>Pts este mes</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>🔥 {data.streak}</Text>
            <Text style={styles.statLabel}>Racha</Text>
          </View>
        </View>

        <TouchableOpacity onPress={logout} style={{marginTop: 30, padding: 15, backgroundColor: '#FEE2E2', borderRadius: 10}}>
          <Text style={{color: '#991B1B', textAlign: 'center', fontWeight: 'bold'}}>Cerrar Sesión</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  scrollContent: { padding: 20 },
  header: { marginBottom: 24 },
  greeting: { fontSize: 28, fontWeight: 'bold', color: '#111827' },
  groupName: { fontSize: 16, color: '#6B7280', marginTop: 4 },
  statsCard: { backgroundColor: '#4F46E5', borderRadius: 16, padding: 20, flexDirection: 'row', justifyContent: 'space-between', marginBottom: 32 },
  statItem: { alignItems: 'center', flex: 1 },
  statValue: { fontSize: 24, fontWeight: 'bold', color: '#fff' },
  statLabel: { fontSize: 12, color: '#E0E7FF', marginTop: 4 },
  divider: { width: 1, backgroundColor: '#6366F1' }
});
"""

# 6. Backend Auth Middleware
os.makedirs(os.path.join(base_dir, "backend/src/middleware"), exist_ok=True)
files["backend/src/middleware/authMiddleware.ts"] = """import { Request, Response, NextFunction } from 'express';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

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
    // Aquí iría la verificación real de Firebase Admin
    // Para no bloquearte si no has puesto las claves de Admin en backend:
    // Asumiremos que el token de dev devuelve siempre al usuario 'alex@test.com' 
    // que creamos en el prisma db seed.
    const user = await prisma.user.findFirst({ where: { email: 'alex@test.com' }});
    if (!user) throw new Error('User not found in DB');
    
    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};
"""

# 7. Backend User Routes and Dashboard
files["backend/src/routes/userRoutes.ts"] = """import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/dashboard', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    
    // Buscar su membresía de grupo
    const membership = await prisma.groupMember.findFirst({
      where: { user_id: user.id },
      include: { group: true }
    });

    res.json({
      name: user.name,
      groupName: membership?.group.name || null,
      totalPoints: membership?.total_points || 0,
      streak: membership?.streak_days || 0,
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
"""

# 8. Update Backend server.ts to include userRoutes
files["backend/src/server.ts"] = """import express from 'express';
import cors from 'cors';
import authRoutes from './routes/authRoutes';
import taskRoutes from './routes/taskRoutes';
import userRoutes from './routes/userRoutes';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/tasks', taskRoutes);
app.use('/api/users', userRoutes);

app.get('/health', (req, res) => res.json({ status: 'ok' }));

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Auth and Home integration completed!")
