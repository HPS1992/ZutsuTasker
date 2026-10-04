import * as Device from 'expo-device';
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
