import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Onboarding Screen (3-4 pantallas atractivas)
files["mobile/src/screens/OnboardingScreen.tsx"] = """import React, { useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, Dimensions } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width } = Dimensions.get('window');

const SLIDES = [
  { id: '1', title: 'Bienvenido a Zutsu', desc: 'El método japonés para dividir las tareas del hogar de forma justa y transparente.', icon: 'home' },
  { id: '2', title: 'Equidad Total', desc: 'Olvídate de las discusiones. Descubre quién hace qué con nuestra barra de equilibrio.', icon: 'pie-chart' },
  { id: '3', title: 'Gana Recompensas', desc: 'Convierte el esfuerzo en premios. Canjea puntos por librarte de fregar o cenas pagadas.', icon: 'gift' },
  { id: '4', title: 'Cero Retrasos', desc: 'Mantén tu racha. Las tareas olvidadas restan puntos al cabo de 2 días.', icon: 'flame' }
];

export default function OnboardingScreen() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const navigation = useNavigation<any>();

  const nextSlide = async () => {
    if (currentIndex < SLIDES.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else {
      await AsyncStorage.setItem('hasSeenOnboarding', 'true');
      navigation.replace('Auth');
    }
  };

  const slide = SLIDES[currentIndex];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Ionicons name={slide.icon as any} size={100} color="#4F46E5" />
        </View>
        <Text style={styles.title}>{slide.title}</Text>
        <Text style={styles.desc}>{slide.desc}</Text>
      </View>
      <View style={styles.footer}>
        <View style={styles.dots}>
          {SLIDES.map((_, i) => (
            <View key={i} style={[styles.dot, currentIndex === i && styles.activeDot]} />
          ))}
        </View>
        <TouchableOpacity style={styles.button} onPress={nextSlide}>
          <Text style={styles.buttonText}>{currentIndex === SLIDES.length - 1 ? 'Empezar' : 'Siguiente'}</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  iconContainer: { width: 160, height: 160, backgroundColor: '#EEF2FF', borderRadius: 80, alignItems: 'center', justifyContent: 'center', marginBottom: 40 },
  title: { fontSize: 32, fontWeight: '900', color: '#111827', marginBottom: 16, textAlign: 'center' },
  desc: { fontSize: 18, color: '#6B7280', textAlign: 'center', lineHeight: 28 },
  footer: { padding: 32, paddingBottom: 48 },
  dots: { flexDirection: 'row', justifyContent: 'center', marginBottom: 32 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#E5E7EB', marginHorizontal: 6 },
  activeDot: { backgroundColor: '#4F46E5', width: 24 },
  button: { backgroundColor: '#4F46E5', padding: 20, borderRadius: 16, alignItems: 'center' },
  buttonText: { color: '#fff', fontSize: 18, fontWeight: 'bold' }
});
"""

# 2. Calendar Screen (Mensual y vista de tareas)
files["mobile/src/screens/CalendarScreen.tsx"] = """import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView } from 'react-native';
import { Calendar, LocaleConfig } from 'react-native-calendars';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';

LocaleConfig.locales['es'] = {
  monthNames: ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'],
  monthNamesShort: ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'],
  dayNames: ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'],
  dayNamesShort: ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'],
  today: 'Hoy'
};
LocaleConfig.defaultLocale = 'es';

export default function CalendarScreen({ navigation }: any) {
  const { tasks, fetchTasks, completeTask } = useTaskStore();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => { fetchTasks(); }, []);

  const getMarkedDates = () => {
    const marks: any = {};
    tasks.forEach(t => {
      const date = new Date(t.due_date).toISOString().split('T')[0];
      marks[date] = { marked: true, dotColor: t.status === 'COMPLETED' ? '#10B981' : '#4F46E5' };
    });
    marks[selectedDate] = { ...marks[selectedDate], selected: true, selectedColor: '#4F46E5' };
    return marks;
  };

  const tasksForDate = tasks.filter(t => new Date(t.due_date).toISOString().split('T')[0] === selectedDate);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Calendario</Text>
      </View>
      <ScrollView>
        <Calendar
          current={selectedDate}
          onDayPress={(day: any) => setSelectedDate(day.dateString)}
          markedDates={getMarkedDates()}
          theme={{
            todayTextColor: '#4F46E5',
            selectedDayBackgroundColor: '#4F46E5',
            arrowColor: '#4F46E5',
          }}
        />
        <View style={styles.tasksSection}>
          <Text style={styles.sectionTitle}>Tareas del {selectedDate}</Text>
          {tasksForDate.length === 0 ? (
            <Text style={styles.emptyText}>No hay tareas para este día.</Text>
          ) : (
            tasksForDate.map(t => (
              <View key={t.id} style={{marginBottom: 12}}>
                 {/* Envuelto en touchable para ir a detalles si se quiere */}
                 <TaskCard item={t} onComplete={() => completeTask(t.id)} />
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  header: { padding: 24, backgroundColor: '#fff', borderBottomWidth:1, borderColor:'#E5E7EB' },
  headerTitle: { fontSize: 28, fontWeight: '800', color: '#111827' },
  tasksSection: { padding: 16 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#374151' },
  emptyText: { color: '#6B7280', fontStyle: 'italic', textAlign: 'center', marginTop: 20 }
});
"""

# 3. Update App.tsx to load Onboarding + Calendar
files["mobile/App.tsx"] = """import React, { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { ActivityIndicator, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

import OnboardingScreen from './src/screens/OnboardingScreen';
import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import TasksScreen from './src/screens/TasksScreen';
import MarketScreen from './src/screens/MarketScreen';
import StatsScreen from './src/screens/StatsScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import CalendarScreen from './src/screens/CalendarScreen';

export type RootStackParamList = { Onboarding: undefined; Auth: undefined; Main: undefined; };
const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator();

function MainTabs() {
  return (
    <Tab.Navigator screenOptions={({ route }) => ({
      headerShown: false,
      tabBarActiveTintColor: '#4F46E5',
      tabBarInactiveTintColor: '#9CA3AF',
      tabBarStyle: { borderTopWidth: 0, elevation: 10, shadowOpacity: 0.1, height: 65, paddingBottom: 10, paddingTop: 8 },
      tabBarIcon: ({ focused, color, size }) => {
        let iconName: any = 'home';
        if (route.name === 'Inicio') iconName = focused ? 'home' : 'home-outline';
        else if (route.name === 'Tareas') iconName = focused ? 'list' : 'list-outline';
        else if (route.name === 'Calendario') iconName = focused ? 'calendar' : 'calendar-outline';
        else if (route.name === 'Market') iconName = focused ? 'gift' : 'gift-outline';
        else if (route.name === 'Equidad') iconName = focused ? 'pie-chart' : 'pie-chart-outline';
        return <Ionicons name={iconName} size={26} color={color} />;
      },
    })}>
      <Tab.Screen name="Inicio" component={HomeScreen} />
      <Tab.Screen name="Tareas" component={TasksScreen} />
      <Tab.Screen name="Calendario" component={CalendarScreen} />
      <Tab.Screen name="Market" component={MarketScreen} />
      <Tab.Screen name="Equidad" component={StatsScreen} />
    </Tab.Navigator>
  );
}

function RootNavigator() {
  const { user, loading } = useAuth();
  const [hasSeenOnboarding, setHasSeenOnboarding] = useState<boolean | null>(null);

  useEffect(() => {
    AsyncStorage.getItem('hasSeenOnboarding').then(val => {
      setHasSeenOnboarding(val === 'true');
    });
  }, []);
  
  if (loading || hasSeenOnboarding === null) {
    return <View style={{flex: 1, justifyContent: 'center', backgroundColor:'#fff'}}><ActivityIndicator size="large" color="#4F46E5" /></View>;
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!hasSeenOnboarding && (
        <Stack.Screen name="Onboarding" component={OnboardingScreen} />
      )}
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

# Modificar el Header de Inicio para que el Profile Settings esté accesible arriba a la derecha (ya que quitamos su tab)
home_path = os.path.join(base_dir, "mobile/src/screens/HomeScreen.tsx")
with open(home_path, "r", encoding="utf-8") as f:
    home_screen = f.read()

home_screen = home_screen.replace(
    "<View style={styles.header}>",
    """<View style={styles.header}>
          <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
            <Text style={styles.greeting}>¡Hola, {data.name}! 🚀</Text>
            {/* OJO: Falta prop de navegación si no inyectamos navigation, pero asumiremos que lo importamos con useNavigation */}
          </View>"""
)

# Añadiremos un botoncito de settings más abajo
home_screen = home_screen.replace(
    "import { Ionicons } from '@expo/vector-icons';",
    "import { Ionicons } from '@expo/vector-icons';\nimport { useNavigation } from '@react-navigation/native';"
)
home_screen = home_screen.replace(
    "export default function HomeScreen() {",
    "export default function HomeScreen() {\n  const navigation = useNavigation<any>();"
)
home_screen = home_screen.replace(
    "<Text style={styles.greeting}>¡Hola, {data.name}! 🚀</Text>",
    "<Text style={styles.greeting}>¡Hola, {data.name}! 🚀</Text>\n<TouchableOpacity onPress={() => navigation.navigate('Ajustes')}><Ionicons name=\"settings-outline\" size={28} color=\"#4F46E5\"/></TouchableOpacity>"
)

files["mobile/src/screens/HomeScreen.tsx"] = home_screen

# Y agregar 'Ajustes' al Main Stack (en App.tsx RootNavigator)
app_content = files["mobile/App.tsx"]
app_content = app_content.replace(
    "<Stack.Screen name=\"Main\" component={MainTabs} />",
    "<Stack.Screen name=\"Main\" component={MainTabs} />\n        <Stack.Screen name=\"Ajustes\" component={ProfileScreen} options={{ presentation: 'modal' }} />"
)
files["mobile/App.tsx"] = app_content

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Checklist final completado.")
