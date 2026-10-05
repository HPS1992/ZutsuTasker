import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface AppUser {
  id: string;
  uid: string;
  email: string;
  displayName: string;
}

function parseUser(value: unknown): AppUser {
  if (!value || typeof value !== 'object') throw new Error('Sesión inválida');
  const data = value as Record<string, unknown>;
  const id = data.id || data.uid;
  const name = data.name ?? data.displayName;
  if (typeof id !== 'string' || typeof data.email !== 'string' || typeof name !== 'string') {
    throw new Error('Sesión inválida');
  }
  return { id, uid: id, email: data.email, displayName: name };
}

interface AuthContextData {
  user: AppUser | null;
  loading: boolean;
  login: (e: string, p: string) => Promise<void>;
  register: (e: string, p: string, n: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const restoreSession = async () => {
      try {
        const [[, token], [, storedUser]] = await AsyncStorage.multiGet(['mockToken', 'mockUser']);
        if (token && storedUser) {
          const restoredUser = parseUser(JSON.parse(storedUser));
          if (active) {
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            setUser(restoredUser);
          }
        }
      } catch (error) {
        console.warn('No se pudo restaurar la sesión', error);
        if (active) delete api.defaults.headers.common['Authorization'];
        await AsyncStorage.multiRemove(['mockToken', 'mockUser']).catch(() => {});
      } finally {
        if (active) setLoading(false);
      }
    };
    void restoreSession();
    return () => { active = false; };
  }, []);

  const saveSession = async (data: { user: unknown; token: unknown }) => {
    const realUser = parseUser(data.user);
    if (typeof data.token !== 'string' || !data.token) throw new Error('Token de sesión inválido');
    await AsyncStorage.multiSet([
      ['mockToken', data.token],
      ['mockUser', JSON.stringify(realUser)],
    ]);
    api.defaults.headers.common['Authorization'] = `Bearer ${data.token}`;
    setUser(realUser);
  };

  const login = async (e: string, p: string) => {
    const res = await api.post('/auth/local-login', { email: e, password: p });
    await saveSession(res.data);
  };

  const register = async (e: string, p: string, name: string) => {
    const res = await api.post('/auth/local-register', { email: e, password: p, name });
    await saveSession(res.data);
  };

  const logout = async () => {
    await AsyncStorage.multiRemove(['mockToken', 'mockUser']);
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
