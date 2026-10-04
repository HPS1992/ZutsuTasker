import React, { createContext, useContext, useEffect, useState } from 'react';
import { User } from 'firebase/auth';
import { api } from '../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

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
    AsyncStorage.getItem('mockToken').then(token => {
      if (token) {
        AsyncStorage.getItem('mockUser').then(usr => {
            if(usr) setUser(JSON.parse(usr));
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            setLoading(false);
        });
      } else {
        setLoading(false);
      }
    });
  }, []);

  const login = async (e: string, p: string) => {
    const res = await api.post('/auth/local-login', { email: e, password: p });
    const realUser = { uid: res.data.user.id, email: res.data.user.email, displayName: res.data.user.name } as User;
    setUser(realUser);
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
    await AsyncStorage.setItem('mockToken', res.data.token);
    await AsyncStorage.setItem('mockUser', JSON.stringify(realUser));
  };

  const register = async (e: string, p: string, name: string) => {
    const res = await api.post('/auth/local-register', { email: e, password: p, name });
    const realUser = { uid: res.data.user.id, email: res.data.user.email, displayName: res.data.user.name } as User;
    setUser(realUser);
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
    await AsyncStorage.setItem('mockToken', res.data.token);
    await AsyncStorage.setItem('mockUser', JSON.stringify(realUser));
  };

  const logout = async () => {
    setUser(null);
    await AsyncStorage.removeItem('mockToken');
    await AsyncStorage.removeItem('mockUser');
    delete api.defaults.headers.common['Authorization'];
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
