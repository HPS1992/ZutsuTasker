import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"

dirs = [
    "mobile/src/components",
    "mobile/src/screens",
    "mobile/src/navigation",
    "mobile/src/services",
    "mobile/src/store",
    "mobile/src/hooks",
    "mobile/src/utils",
    "mobile/src/assets",
    "mobile/src/config",
    "backend/src/routes",
    "backend/src/controllers",
    "backend/src/services",
    "backend/src/models",
    "backend/src/middleware",
    "backend/src/config",
    "backend/prisma"
]

for d in dirs:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

files = {}

files["TECH_STACK_AND_ROADMAP.md"] = """# Zutsu Tasker - Guía de Inicio Rápido y Arquitectura

## 1. Stack Tecnológico Seleccionado
*   **Frontend Móvil:** **React Native con Expo**. Justificación: Permite iterar rapidísimo, compartir código al 100% entre iOS y Android, y facilita el acceso a APIs nativas sin configuraciones complejas iniciales.
*   **Backend:** **Node.js con Express y TypeScript**. Justificación: Ligero, gran ecosistema, el equipo puede usar TypeScript en todo el stack (Full-Stack TS), reduciendo la fricción mental de cambiar de lenguaje.
*   **Base de Datos:** **PostgreSQL** (gestionado vía **Prisma ORM**). Justificación: El modelo de Zutsu es altamente relacional (usuarios -> grupos -> tareas -> historiales de puntos). PostgreSQL asegura integridad referencial y Prisma da un tipado estricto espectacular.
*   **Autenticación:** **Firebase Auth**. Justificación: Implementación de SSO (Google/Apple) trivial en móviles, gestión segura de sesiones, y tokens JWT fáciles de verificar en nuestro backend Node.
*   **Notificaciones Push:** **Expo Push Notifications**. Justificación: Ya viene integrado con Expo, abstrayendo la complejidad enorme de APNs (Apple) y FCM (Android).

## 2. Estructura de Carpetas Frontend (React Native + Expo)
```
mobile/
├── App.tsx                 # Punto de entrada y configuración de navegación raíz
├── app.json                # Configuración de Expo
├── src/
│   ├── assets/             # Imágenes, iconos, fuentes locales
│   ├── components/         # Componentes UI reutilizables (Botones, Tarjetas, Modales)
│   ├── config/             # Variables de entorno, constantes, temas (colores)
│   ├── hooks/              # Custom hooks (ej. useAuth, useTasks)
│   ├── navigation/         # Definición de Stacks y Tabs de React Navigation
│   ├── screens/            # Pantallas completas (Home, Login, Tareas)
│   ├── services/           # Llamadas a la API backend (axios/fetch), integración Firebase
│   ├── store/              # Estado global (Zustand o Context API)
│   └── utils/              # Funciones helper (formateo de fechas, cálculo de puntos local)
```

## 3. Modelo de Datos Concreto (PostgreSQL + Prisma)
Ver archivo `backend/prisma/schema.prisma` para la definición exacta. Entidades principales:
*   `User`: id, email, name.
*   `Group`: id, name.
*   `GroupMember`: une usuario y grupo con su rol y puntos actuales.
*   `TaskTemplate`: base de las tareas. Define la complejidad y puntos base.
*   `TaskInstance`: la tarea concreta asignada a una fecha y un usuario. status, points_awarded.
*   `PointsLog`: registro inmutable de cada ganancia/pérdida de puntos para auditoría y gráficas.
*   `Reward` / `RewardRedemption`: catálogo y registro de canjes.

## 4. Instrucciones de Puesta en Marcha

### Backend
1. `cd backend`
2. Inicializa el proyecto: `npm init -y`
3. Instala dependencias: `npm i express cors dotenv prisma @prisma/client`
4. Dependencias de desarrollo: `npm i -D typescript @types/express @types/node @types/cors ts-node-dev`
5. Inicializa TypeScript: `npx tsc --init`
6. Levanta una base de datos PostgreSQL local (ej. vía Docker: `docker run --name zutsu-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres`)
7. Configura el `.env` en backend: `DATABASE_URL="postgresql://postgres:postgres@localhost:5432/zutsu?schema=public"`
8. Sincroniza la BD: `npx prisma db push`
9. Inserta datos de prueba: `npx prisma db seed` (requiere configurar ts-node en package.json)
10. Corre el server: `npm run dev` (usando ts-node-dev src/server.ts)

### Frontend
1. `cd mobile`
2. Si no lo has hecho, inicializa expo: `npx create-expo-app . -t expo-template-blank-typescript`
3. Instala dependencias de navegación: `npm install @react-navigation/native @react-navigation/native-stack @react-navigation/bottom-tabs react-native-screens react-native-safe-area-context`
4. Levanta el emulador o app: `npm start` (abre Expo Go en tu móvil o simulador)

## 5. Hoja de Ruta Sugerida (Próximas iteraciones)

*   **Iteración 1: Core Foundation.** 
    *   Setup de Firebase Auth.
    *   Creación de Grupos e Invitaciones.
    *   Listado básico de tareas consumiendo la API.
*   **Iteración 2: Motor de Tareas.** 
    *   Creación de tareas (templates y asignaciones).
    *   Endpoint para completar tareas de forma transaccional.
    *   Suma de puntos reflejada en la Home.
*   **Iteración 3: Gamificación & Market.** 
    *   Creación visual del Market.
    *   Lógica de descuento de puntos al canjear.
    *   Penalizaciones automáticas por retraso (Cron Job en backend).
*   **Iteración 4: Rotación y Equidad.** 
    *   Implementación del algoritmo de rotación automática.
    *   Gráficos visuales de equidad en la vista de Estadísticas.
*   **Iteración 5: Refinamiento.** 
    *   Expo Push Notifications.
    *   Calendario interactivo (react-native-calendars).
    *   Pulido de animaciones y microinteracciones (Lottie/Reanimated).
"""

files["mobile/App.tsx"] = """import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

// Import screens
import OnboardingScreen from './src/screens/OnboardingScreen';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import TasksScreen from './src/screens/TasksScreen';

// Types for navigation
export type RootStackParamList = {
  Onboarding: undefined;
  Auth: undefined;
  Main: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

// Bottom Tabs for main app
function MainTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Tareas" component={TasksScreen} />
      {/* Pendientes de implementar en futuras iteraciones:
      <Tab.Screen name="Calendario" component={CalendarScreen} />
      <Tab.Screen name="Estadísticas" component={StatsScreen} />
      <Tab.Screen name="Market" component={MarketScreen} />
      */}
    </Tab.Navigator>
  );
}

export default function App() {
  // Lógica mockeada. En prod se leería de AsyncStorage y Context/Zustand
  const isFirstLaunch = true; 
  const isAuthenticated = false;

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {isFirstLaunch && (
          <Stack.Screen name="Onboarding" component={OnboardingScreen} />
        )}
        {!isAuthenticated ? (
          <Stack.Screen name="Auth" component={LoginScreen} />
        ) : (
          <Stack.Screen name="Main" component={MainTabs} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
"""

files["mobile/src/screens/OnboardingScreen.tsx"] = """import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView } from 'react-native';

const SLIDES = [
  {
    id: 1,
    title: 'El fin del "te toca a ti"',
    description: 'Organiza y reparte las tareas del hogar de forma transparente. Con Zutsu, siempre sabrás quién hace qué.',
  },
  {
    id: 2,
    title: 'Completa y acumula puntos',
    description: 'Cada tarea tiene un valor basado en su esfuerzo. Haz tu parte, mantén tu racha y sube en el ranking.',
  },
  {
    id: 3,
    title: 'Tu esfuerzo tiene premio',
    description: 'Canjea tus puntos en el Market por recompensas que el resto del grupo deberá cumplir por ti.',
  }
];

export default function OnboardingScreen({ navigation }: any) {
  const [currentSlide, setCurrentSlide] = useState(0);

  const nextSlide = () => {
    if (currentSlide < SLIDES.length - 1) {
      setCurrentSlide(currentSlide + 1);
    } else {
      navigation.replace('Auth');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.stepIndicator}>{currentSlide + 1} / {SLIDES.length}</Text>
        <View style={styles.illustrationPlaceholder}>
          <Text style={styles.illustrationText}>[Ilustración {currentSlide + 1}]</Text>
        </View>
        <Text style={styles.title}>{SLIDES[currentSlide].title}</Text>
        <Text style={styles.description}>{SLIDES[currentSlide].description}</Text>
      </View>
      
      <TouchableOpacity style={styles.button} onPress={nextSlide}>
        <Text style={styles.buttonText}>
          {currentSlide === SLIDES.length - 1 ? 'Empezar' : 'Siguiente'}
        </Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', justifyContent: 'space-between' },
  content: { flex: 1, alignItems: 'center', padding: 20, justifyContent: 'center' },
  stepIndicator: { fontSize: 16, color: '#888', marginBottom: 20 },
  illustrationPlaceholder: { width: 250, height: 250, backgroundColor: '#E0E7FF', borderRadius: 20, justifyContent: 'center', alignItems: 'center', marginBottom: 40 },
  illustrationText: { color: '#4F46E5', fontWeight: 'bold' },
  title: { fontSize: 24, fontWeight: 'bold', textAlign: 'center', marginBottom: 15, color: '#1F2937' },
  description: { fontSize: 16, textAlign: 'center', color: '#4B5563', lineHeight: 24, paddingHorizontal: 20 },
  button: { backgroundColor: '#4F46E5', padding: 18, margin: 20, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontSize: 18, fontWeight: 'bold' }
});
"""

files["mobile/src/screens/LoginScreen.tsx"] = """import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, SafeAreaView } from 'react-native';

export default function LoginScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = () => {
    // Simular login exitoso -> navega al Main Tab Navigator
    navigation.replace('Main');
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.formContainer}>
        <Text style={styles.header}>Zutsu Tasker</Text>
        <Text style={styles.subHeader}>El equilibrio empieza en casa</Text>

        <TextInput
          style={styles.input}
          placeholder="Correo electrónico"
          keyboardType="email-address"
          autoCapitalize="none"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="Contraseña"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity style={styles.primaryButton} onPress={handleLogin}>
          <Text style={styles.primaryButtonText}>Iniciar Sesión</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>Crear una cuenta nueva</Text>
        </TouchableOpacity>

        <View style={styles.ssoContainer}>
          <Text style={styles.ssoText}>O continúa con</Text>
          <View style={styles.ssoButtonsRow}>
            <TouchableOpacity style={styles.ssoButton}><Text style={styles.ssoBtnText}>Google</Text></TouchableOpacity>
            <TouchableOpacity style={styles.ssoButton}><Text style={styles.ssoBtnText}>Apple</Text></TouchableOpacity>
          </View>
        </View>
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
  ssoContainer: { marginTop: 40, alignItems: 'center' },
  ssoText: { color: '#6B7280', marginBottom: 16 },
  ssoButtonsRow: { flexDirection: 'row', gap: 16 },
  ssoButton: { flex: 1, padding: 14, borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 10, alignItems: 'center' },
  ssoBtnText: { fontWeight: '600', color: '#374151' }
});
"""

files["mobile/src/screens/HomeScreen.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, TouchableOpacity } from 'react-native';

export default function HomeScreen({ navigation }: any) {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <Text style={styles.greeting}>Hola, Álex 👋</Text>
          <Text style={styles.groupName}>Piso Estudiantes</Text>
        </View>

        <View style={styles.statsCard}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>450</Text>
            <Text style={styles.statLabel}>Pts Totales</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>120</Text>
            <Text style={styles.statLabel}>Pts este mes</Text>
          </View>
          <View style={styles.divider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>🔥 4</Text>
            <Text style={styles.statLabel}>Racha (días)</Text>
          </View>
        </View>

        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Tus tareas pendientes</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Tareas')}>
            <Text style={styles.seeAll}>Ver todas</Text>
          </TouchableOpacity>
        </View>

        {/* Lista simulada de tareas rápidas */}
        <View style={styles.taskCard}>
          <View style={styles.taskInfo}>
            <Text style={styles.taskTitle}>Bajar la basura</Text>
            <Text style={styles.taskSubtitle}>Hoy, 20:00 • Cocina</Text>
          </View>
          <View style={styles.pointsBadge}>
            <Text style={styles.pointsText}>+15 pts</Text>
          </View>
        </View>

        <View style={styles.taskCard}>
          <View style={styles.taskInfo}>
            <Text style={styles.taskTitle}>Limpiar el baño</Text>
            <Text style={styles.taskSubtitle}>Mañana • Limpieza</Text>
          </View>
          <View style={styles.pointsBadge}>
            <Text style={styles.pointsText}>+50 pts</Text>
          </View>
        </View>

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
  statsCard: { backgroundColor: '#4F46E5', borderRadius: 16, padding: 20, flexDirection: 'row', justifyContent: 'space-between', marginBottom: 32, shadowColor: '#4F46E5', shadowOpacity: 0.3, shadowRadius: 10, elevation: 5 },
  statItem: { alignItems: 'center', flex: 1 },
  statValue: { fontSize: 24, fontWeight: 'bold', color: '#fff' },
  statLabel: { fontSize: 12, color: '#E0E7FF', marginTop: 4 },
  divider: { width: 1, backgroundColor: '#6366F1' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', color: '#1F2937' },
  seeAll: { color: '#4F46E5', fontWeight: '600' },
  taskCard: { backgroundColor: '#fff', padding: 16, borderRadius: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, borderWidth: 1, borderColor: '#F3F4F6' },
  taskInfo: { flex: 1 },
  taskTitle: { fontSize: 16, fontWeight: '600', color: '#1F2937' },
  taskSubtitle: { fontSize: 13, color: '#6B7280', marginTop: 4 },
  pointsBadge: { backgroundColor: '#DEF7EC', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 20 },
  pointsText: { color: '#046C4E', fontWeight: 'bold', fontSize: 12 }
});
"""

files["mobile/src/screens/TasksScreen.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity } from 'react-native';

const MOCK_TASKS = [
  { id: '1', title: 'Bajar la basura', category: 'Cocina', points: 15, status: 'pending', assignee: 'Álex', date: 'Hoy' },
  { id: '2', title: 'Limpiar el baño', category: 'Limpieza', points: 50, status: 'pending', assignee: 'Álex', date: 'Mañana' },
  { id: '3', title: 'Comprar pan', category: 'Compras', points: 10, status: 'completed', assignee: 'María', date: 'Ayer' },
  { id: '4', title: 'Cambiar arenero', category: 'Mascotas', points: 30, status: 'pending', assignee: 'Sin asignar', date: 'Hoy' },
];

export default function TasksScreen() {
  const renderItem = ({ item }: any) => (
    <View style={styles.taskCard}>
      <View style={styles.taskHeader}>
        <Text style={styles.taskTitle}>{item.title}</Text>
        <Text style={[styles.statusBadge, item.status === 'completed' ? styles.statusCompleted : styles.statusPending]}>
          {item.status === 'completed' ? 'Hecho' : 'Pendiente'}
        </Text>
      </View>
      <View style={styles.taskDetails}>
        <Text style={styles.taskDetailText}>Cat: {item.category}</Text>
        <Text style={styles.taskDetailText}>👤 {item.assignee}</Text>
        <Text style={styles.taskDetailText}>📅 {item.date}</Text>
      </View>
      <View style={styles.taskFooter}>
        <Text style={styles.pointsText}>+{item.points} pts</Text>
        {item.status === 'pending' && (
          <TouchableOpacity style={styles.actionButton}>
            <Text style={styles.actionButtonText}>Completar</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Todas las tareas</Text>
      </View>
      
      <FlatList
        data={MOCK_TASKS}
        keyExtractor={item => item.id}
        renderItem={renderItem}
        contentContainerStyle={styles.listContainer}
      />

      <TouchableOpacity style={styles.fab}>
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  header: { padding: 20, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  headerTitle: { fontSize: 24, fontWeight: 'bold', color: '#1F2937' },
  listContainer: { padding: 16 },
  taskCard: { backgroundColor: '#fff', padding: 16, borderRadius: 12, marginBottom: 12, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 5, elevation: 2 },
  taskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  taskTitle: { fontSize: 18, fontWeight: 'bold', color: '#1F2937' },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6, overflow: 'hidden', fontSize: 12, fontWeight: 'bold' },
  statusPending: { backgroundColor: '#FEF3C7', color: '#92400E' },
  statusCompleted: { backgroundColor: '#DEF7EC', color: '#046C4E' },
  taskDetails: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  taskDetailText: { fontSize: 13, color: '#6B7280' },
  taskFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderTopWidth: 1, borderTopColor: '#F3F4F6', paddingTop: 12 },
  pointsText: { fontSize: 16, fontWeight: 'bold', color: '#4F46E5' },
  actionButton: { backgroundColor: '#10B981', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8 },
  actionButtonText: { color: '#fff', fontWeight: 'bold' },
  fab: { position: 'absolute', bottom: 24, right: 24, width: 60, height: 60, borderRadius: 30, backgroundColor: '#4F46E5', justifyContent: 'center', alignItems: 'center', shadowColor: '#4F46E5', shadowOpacity: 0.4, shadowRadius: 10, elevation: 5 },
  fabText: { fontSize: 32, color: '#fff', fontWeight: '300', marginTop: -2 }
});
"""

files["backend/prisma/schema.prisma"] = """generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id             String         @id @default(uuid())
  email          String         @unique
  name           String
  avatar_url     String?
  created_at     DateTime       @default(now())
  memberships    GroupMember[]
  tasks_assigned TaskInstance[] @relation("AssignedUser")
  points_logs    PointsLog[]
  redemptions    RewardRedemption[]
}

model Group {
  id            String         @id @default(uuid())
  name          String
  created_at    DateTime       @default(now())
  penalty_config Json?         // e.g. { "type": "percentage", "value": 50 }
  members       GroupMember[]
  templates     TaskTemplate[]
  instances     TaskInstance[]
  rewards       Reward[]
}

model GroupMember {
  user_id       String
  group_id      String
  role          String         // ADMIN | MEMBER
  total_points  Int            @default(0)
  streak_days   Int            @default(0)
  joined_at     DateTime       @default(now())

  user          User           @relation(fields: [user_id], references: [id])
  group         Group          @relation(fields: [group_id], references: [id])

  @@id([user_id, group_id])
}

model TaskTemplate {
  id            String         @id @default(uuid())
  group_id      String
  title         String
  category      String
  duration_min  Int
  complexity    Int            // 1=Baja, 2=Media, 3=Alta
  base_points   Int
  is_active     Boolean        @default(true)
  
  group         Group          @relation(fields: [group_id], references: [id])
  instances     TaskInstance[]
}

model TaskInstance {
  id            String         @id @default(uuid())
  template_id   String
  group_id      String
  assigned_to   String?        // user_id nullable si está sin asignar
  due_date      DateTime
  status        String         @default("PENDING") // PENDING, COMPLETED, EXPIRED
  completed_at  DateTime?
  points_awarded Int?
  
  template      TaskTemplate   @relation(fields: [template_id], references: [id])
  group         Group          @relation(fields: [group_id], references: [id])
  user          User?          @relation("AssignedUser", fields: [assigned_to], references: [id])
}

model Reward {
  id            String         @id @default(uuid())
  group_id      String
  title         String
  cost_points   Int
  yearly_limit  Int?
  
  group         Group          @relation(fields: [group_id], references: [id])
  redemptions   RewardRedemption[]
}

model RewardRedemption {
  id            String         @id @default(uuid())
  reward_id     String
  user_id       String
  redeemed_at   DateTime       @default(now())

  reward        Reward         @relation(fields: [reward_id], references: [id])
  user          User           @relation(fields: [user_id], references: [id])
}

model PointsLog {
  id            String         @id @default(uuid())
  user_id       String
  group_id      String
  amount        Int
  reason        String         // TASK_COMPLETED, PENALTY, REWARD_CLAIM
  timestamp     DateTime       @default(now())

  user          User           @relation(fields: [user_id], references: [id])
}
"""

files["backend/src/server.ts"] = """import express from 'express';
import cors from 'cors';
import authRoutes from './routes/authRoutes';
import taskRoutes from './routes/taskRoutes';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/tasks', taskRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok', message: 'Zutsu Tasker API is running' });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
"""

files["backend/src/routes/authRoutes.ts"] = """import { Router } from 'express';
import { register, login } from '../controllers/authController';

const router = Router();

router.post('/register', register);
router.post('/login', login);

export default router;
"""

files["backend/src/routes/taskRoutes.ts"] = """import { Router } from 'express';
import { listTasks, createTask, completeTask } from '../controllers/taskController';

const router = Router();

// Pendiente: Middleware de autenticación (ej. verifyToken) antes de estas rutas
router.get('/', listTasks);
router.post('/', createTask);
router.post('/:id/complete', completeTask);

export default router;
"""

files["backend/src/controllers/authController.ts"] = """import { Request, Response } from 'express';
import { authService } from '../services/authService';

export const register = async (req: Request, res: Response) => {
  try {
    const { email, name, firebase_uid } = req.body;
    const user = await authService.registerUser(email, name, firebase_uid);
    res.status(201).json(user);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};

export const login = async (req: Request, res: Response) => {
  try {
    const { firebase_uid } = req.body;
    const user = await authService.loginUser(firebase_uid);
    res.status(200).json(user);
  } catch (error: any) {
    res.status(401).json({ error: error.message });
  }
};
"""

files["backend/src/controllers/taskController.ts"] = """import { Request, Response } from 'express';
import { taskService } from '../services/taskService';

export const listTasks = async (req: Request, res: Response) => {
  try {
    const { groupId } = req.query;
    // req.user_id vendría del middleware de auth
    const tasks = await taskService.getGroupTasks(groupId as string);
    res.status(200).json(tasks);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
};

export const createTask = async (req: Request, res: Response) => {
  try {
    const data = req.body;
    const newTask = await taskService.createTaskInstance(data);
    res.status(201).json(newTask);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};

export const completeTask = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { userId } = req.body; // idealmente desde req.user inyectado por middleware
    const result = await taskService.completeTask(id, userId);
    res.status(200).json(result);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};
"""

files["backend/src/services/authService.ts"] = """// import prisma from '../config/prismaClient'; // Simulado

export const authService = {
  async registerUser(email: string, name: string, firebase_uid: string) {
    // 1. Verificar si el usuario ya existe en base de datos PostgreSQL
    // 2. Si no, crearlo: prisma.user.create(...)
    // Retornamos un mock por ahora
    return { id: 'u123', email, name };
  },

  async loginUser(firebase_uid: string) {
    // 1. Buscar usuario por el UID provisto por el token de Firebase
    // 2. Retornar perfil y grupos asociados
    return { id: 'u123', name: 'Álex', token: 'fake_jwt_token' };
  }
};
"""

files["backend/src/services/taskService.ts"] = """// import prisma from '../config/prismaClient'; // Simulado

export const taskService = {
  async getGroupTasks(groupId: string) {
    // prisma.taskInstance.findMany({ where: { group_id: groupId } })
    return [
      { id: 't1', title: 'Bajar la basura', status: 'PENDING', points_awarded: null }
    ];
  },

  async createTaskInstance(data: any) {
    // prisma.taskInstance.create(...)
    return { id: 't2', ...data, status: 'PENDING' };
  },

  async completeTask(taskId: string, userId: string) {
    // 1. Verificar que la tarea existe y está PENDING
    // 2. Actualizar status a COMPLETED, asignar fecha de completado
    // 3. Obtener template_id para saber cuántos puntos base otorga
    // 4. Crear registro en PointsLog
    // 5. Sumar puntos al GroupMember (userId, groupId)
    // Todo esto debería ir en una transacción Prisma ($transaction)
    
    return { success: true, message: 'Tarea completada, +15 puntos' };
  }
};
"""

files["backend/prisma/seed.ts"] = """import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Iniciando seed de datos falsos...');

  // 1. Crear usuarios
  const user1 = await prisma.user.create({ data: { email: 'alex@test.com', name: 'Álex' } });
  const user2 = await prisma.user.create({ data: { email: 'maria@test.com', name: 'María' } });
  const user3 = await prisma.user.create({ data: { email: 'carlos@test.com', name: 'Carlos' } });

  // 2. Crear Grupo
  const group = await prisma.group.create({
    data: { name: 'Piso Estudiantes' }
  });

  // 3. Asociar miembros al grupo
  await prisma.groupMember.createMany({
    data: [
      { user_id: user1.id, group_id: group.id, role: 'ADMIN', total_points: 120 },
      { user_id: user2.id, group_id: group.id, role: 'MEMBER', total_points: 95 },
      { user_id: user3.id, group_id: group.id, role: 'MEMBER', total_points: 40 },
    ]
  });

  // 4. Crear Plantillas de tareas
  const template1 = await prisma.taskTemplate.create({
    data: { group_id: group.id, title: 'Bajar basura', category: 'Cocina', duration_min: 5, complexity: 1, base_points: 10 }
  });
  const template2 = await prisma.taskTemplate.create({
    data: { group_id: group.id, title: 'Limpiar Baño', category: 'Limpieza', duration_min: 30, complexity: 3, base_points: 50 }
  });

  // 5. Crear Instancias de Tareas (asignadas y sin asignar)
  await prisma.taskInstance.create({
    data: { template_id: template1.id, group_id: group.id, assigned_to: user1.id, due_date: new Date(), status: 'PENDING' }
  });
  await prisma.taskInstance.create({
    data: { template_id: template2.id, group_id: group.id, assigned_to: user2.id, due_date: new Date(), status: 'COMPLETED', completed_at: new Date(), points_awarded: 50 }
  });

  // 6. Crear Recompensas en el Market
  await prisma.reward.create({
    data: { group_id: group.id, title: 'Librarse de fregar', cost_points: 100, yearly_limit: 5 }
  });
  await prisma.reward.create({
    data: { group_id: group.id, title: 'Cena pagada por los demás', cost_points: 1000, yearly_limit: 1 }
  });

  console.log('Seed finalizado con éxito. Grupo, Usuarios, Tareas y Recompensas creados.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Estructura base de Zutsu Tasker generada exitosamente.")
