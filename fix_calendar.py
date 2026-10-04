import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile"

# 1. Update App.tsx
app_path = os.path.join(base_dir, "App.tsx")
with open(app_path, "r") as f:
    app = f.read()

app = app.replace(
    "import TasksScreen from './src/screens/TasksScreen';",
    "import TasksScreen from './src/screens/TasksScreen';\nimport CalendarScreen from './src/screens/CalendarScreen';"
)

app = app.replace(
    "if (route.name === 'Tareas') iconName = focused ? 'checkbox' : 'checkbox-outline';",
    "if (route.name === 'Tareas') iconName = focused ? 'checkbox' : 'checkbox-outline';\n          else if (route.name === 'Calendario') iconName = focused ? 'calendar' : 'calendar-outline';"
)

app = app.replace(
    "<Tab.Screen name=\"Tareas\" component={TasksScreen} />",
    "<Tab.Screen name=\"Tareas\" component={TasksScreen} />\n      <Tab.Screen name=\"Calendario\" component={CalendarScreen} />"
)

with open(app_path, "w") as f:
    f.write(app)

# 2. Update CalendarScreen.tsx
cs_path = os.path.join(base_dir, "src/screens/CalendarScreen.tsx")
with open(cs_path, "r") as f:
    cs = f.read()

# Add LinearGradient import
if "LinearGradient" not in cs:
    cs = cs.replace(
        "import { Calendar, LocaleConfig } from 'react-native-calendars';",
        "import { Calendar, LocaleConfig } from 'react-native-calendars';\nimport { LinearGradient } from 'expo-linear-gradient';\nimport { Platform } from 'react-native';"
    )

# Replace the plain header with the gradient header
gradient_header = """
      <LinearGradient colors={['#4F46E5', '#7C3AED']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
            <Text style={styles.headerTitle}>Calendario</Text>
            <Text style={styles.subtitle}>Planificación mensual</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>
"""
old_header = """
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Calendario</Text>
      </View>
"""
cs = cs.replace(old_header.strip(), gradient_header.strip())
cs = cs.replace("<SafeAreaView style={styles.container}>", "<View style={styles.container}>")
cs = cs.replace("</SafeAreaView>", "</View>")

styles_header_gradient = """
  headerGradient: { paddingBottom: 24, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, shadowColor: '#4F46E5', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24 },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.8)', marginTop: 4, fontSize: 16, fontWeight: '500' },
"""
cs = cs.replace("header: { padding: 24, backgroundColor: '#fff', borderBottomWidth:1, borderColor:'#E5E7EB' },\n  headerTitle: { fontSize: 28, fontWeight: '800', color: '#111827' },", styles_header_gradient)

# Ensure currentUserId is passed correctly so TaskCard works without crashing
cs = cs.replace(
    "const { tasks, fetchTasks, completeTask } = useTaskStore();",
    "const { tasks, fetchTasks, completeTask } = useTaskStore();\n  const { user } = require('../context/AuthContext').useAuth();\n  const currentUserId = user?.id || user?.uid;"
)
cs = cs.replace(
    "<TaskCard item={t} onComplete={() => completeTask(t.id)} />",
    "<TaskCard item={t} currentUserId={currentUserId} onComplete={() => completeTask(t.id)} />"
)

with open(cs_path, "w") as f:
    f.write(cs)


# 3. Fix FAB styling in TasksScreen and MarketScreen
ts_path = os.path.join(base_dir, "src/screens/TasksScreen.tsx")
with open(ts_path, "r") as f:
    ts = f.read()
ts = ts.replace("shadowOffset: { width: 0, height: 8 } },", "shadowOffset: { width: 0, height: 8 }, borderRadius: 32, backgroundColor: 'transparent' },")
with open(ts_path, "w") as f:
    f.write(ts)

ms_path = os.path.join(base_dir, "src/screens/MarketScreen.tsx")
with open(ms_path, "r") as f:
    ms = f.read()
ms = ms.replace("shadowOffset: { width: 0, height: 8 } },", "shadowOffset: { width: 0, height: 8 }, borderRadius: 32, backgroundColor: 'transparent' },")
with open(ms_path, "w") as f:
    f.write(ms)

print("Calendar restored and FAB fixed.")
