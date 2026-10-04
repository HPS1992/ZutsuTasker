import os
import subprocess

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. CI/CD GitHub Actions
os.makedirs(os.path.join(base_dir, ".github/workflows"), exist_ok=True)
files[".github/workflows/ci.yml"] = """name: Zutsu Tasker CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  backend-checks:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '20'
    - name: Install dependencies
      working-directory: ./backend
      run: npm ci
    - name: Check TypeScript compilation
      working-directory: ./backend
      run: npm run build

  mobile-checks:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '20'
    - name: Install dependencies
      working-directory: ./mobile
      run: npm ci
    - name: Check Expo build format
      working-directory: ./mobile
      run: npx expo export --platform web
"""

# 2. Actualizar Schema para Push Tokens
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

if "push_token" not in schema:
    schema = schema.replace(
        "task_instances   TaskInstance[]     @relation(\"AssignedUser\")",
        "task_instances   TaskInstance[]     @relation(\"AssignedUser\")\n  push_token       String?            // Para Expo Push Notifications"
    )
files["backend/prisma/schema.prisma"] = schema

# 3. Frontend: Servicio de Notificaciones
files["mobile/src/services/notifications.ts"] = """import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import { api } from './api';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function registerForPushNotificationsAsync() {
  let token;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF231F7C',
    });
  }

  if (Device.isDevice) {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== 'granted') {
      console.log('Permiso denegado para notificaciones push');
      return;
    }
    
    // Obtener token (Requiere projectId en app.json, simulado aquí)
    try {
        const projectId = "tu-project-id-de-expo"; // Se llenaría con Constants.expoConfig.extra.eas.projectId
        token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
        // Enviar al backend
        await api.post('/users/push-token', { token });
    } catch(e) {
        console.log('No se pudo obtener el token en modo web/simulador');
    }
  }

  return token;
}
"""

# 4. Backend: Guardar Token y Servicio de Notificaciones
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
      groupName: member ? member.group.name : null
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

files["backend/src/services/notificationService.ts"] = """import { Expo } from 'expo-server-sdk';
import { PrismaClient } from '@prisma/client';

const expo = new Expo();
const prisma = new PrismaClient();

export const notificationService = {
  async notifyGroup(groupId: string, title: string, body: string, excludeUserId?: string) {
    const members = await prisma.groupMember.findMany({
      where: { group_id: groupId },
      include: { user: true }
    });

    const messages: any[] = [];
    for (const member of members) {
      if (member.user_id === excludeUserId) continue;
      
      const pushToken = member.user.push_token;
      if (pushToken && Expo.isExpoPushToken(pushToken)) {
        messages.push({
          to: pushToken,
          sound: 'default',
          title,
          body,
          data: { groupId },
        });
      }
    }

    const chunks = expo.chunkPushNotifications(messages);
    for (const chunk of chunks) {
      try {
        await expo.sendPushNotificationsAsync(chunk);
      } catch (error) {
        console.error('Error enviando push notifications', error);
      }
    }
  }
};
"""

# Modificar taskService.ts para disparar notificaciones
task_service_path = os.path.join(base_dir, "backend/src/services/taskService.ts")
with open(task_service_path, "r", encoding="utf-8") as f:
    task_service = f.read()

task_service = "import { notificationService } from './notificationService';\n" + task_service
task_service = task_service.replace(
    "return { success: true, message: `Tarea completada, +${points} puntos` };",
    "// Enviar notificaciones al resto del grupo\n    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien acaba de completar: ${task.template.title}`, userId);\n\n    return { success: true, message: `Tarea completada, +${points} puntos` };"
)
files["backend/src/services/taskService.ts"] = task_service

# 5. Integrar notificaciones en el Frontend (HomeScreen)
home_path = os.path.join(base_dir, "mobile/src/screens/HomeScreen.tsx")
with open(home_path, "r", encoding="utf-8") as f:
    home_screen = f.read()

home_screen = home_screen.replace(
    "import { api } from '../services/api';",
    "import { api } from '../services/api';\nimport { registerForPushNotificationsAsync } from '../services/notifications';"
)
home_screen = home_screen.replace(
    "api.get('/users/dashboard').then(res => setData(res.data)).catch(console.error);",
    "api.get('/users/dashboard').then(res => setData(res.data)).catch(console.error);\n    registerForPushNotificationsAsync();"
)
files["mobile/src/screens/HomeScreen.tsx"] = home_screen

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Notificaciones Push y CI/CD configurados.")
