import { initializeApp } from 'firebase/app';
import { getAuth, initializeAuth, getReactNativePersistence, browserLocalPersistence } from 'firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

const getEnv = (key: string, fallback: string) => {
  if (typeof process !== 'undefined' && process.env && process.env[key]) {
    return process.env[key];
  }
  return fallback;
};

const firebaseConfig = {
  apiKey: getEnv('EXPO_PUBLIC_FIREBASE_API_KEY', "TU_API_KEY"),
  authDomain: getEnv('EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN', "zutsu-tasker.firebaseapp.com"),
  projectId: getEnv('EXPO_PUBLIC_FIREBASE_PROJECT_ID', "zutsu-tasker"),
  storageBucket: getEnv('EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET', "zutsu-tasker.appspot.com"),
  messagingSenderId: getEnv('EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID', "123456789"),
  appId: getEnv('EXPO_PUBLIC_FIREBASE_APP_ID', "1:123456789:web:abcdef")
};

const app = initializeApp(firebaseConfig);
export const auth = initializeAuth(app, {
  persistence: Platform.OS === 'web' ? browserLocalPersistence : getReactNativePersistence(AsyncStorage)
});
