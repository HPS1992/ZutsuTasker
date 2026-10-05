import { getApp, getApps, initializeApp } from 'firebase/app';
import * as FirebaseAuth from 'firebase/auth';
import type { Persistence } from 'firebase/auth';
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

const app = getApps().length ? getApp() : initializeApp(firebaseConfig);

function getPersistence(): Persistence {
  if (Platform.OS === 'web') return FirebaseAuth.browserLocalPersistence;
  // This export is available in Firebase's React Native entry, but absent from its web typings.
  if ('getReactNativePersistence' in FirebaseAuth && typeof FirebaseAuth.getReactNativePersistence === 'function') {
    return FirebaseAuth.getReactNativePersistence(AsyncStorage) as Persistence;
  }
  throw new Error('Firebase no ha cargado la implementación de React Native');
}

function initializeFirebaseAuth() {
  try {
    return FirebaseAuth.initializeAuth(app, { persistence: getPersistence() });
  } catch (error) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'auth/already-initialized') {
      return FirebaseAuth.getAuth(app);
    }
    throw error;
  }
}

export const auth = initializeFirebaseAuth();
