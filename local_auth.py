import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Backend Auth Routes for local Auth
files["backend/src/routes/authRoutes.ts"] = """import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import jwt from 'jsonwebtoken';

const router = Router();
const prisma = new PrismaClient();

router.post('/register', async (req, res) => {
  try {
    const { email, name, firebase_uid } = req.body;
    const user = await prisma.user.create({ data: { email, name } });
    res.json(user);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

router.post('/local-register', async (req, res) => {
  try {
    const { email, name } = req.body;
    let user = await prisma.user.findUnique({ where: { email } });
    if (!user) {
      user = await prisma.user.create({ data: { email, name } });
      
      // Auto-join al primer grupo (Piso Estudiantes) para que puedan probar la app
      const group = await prisma.group.findFirst();
      if (group) {
        await prisma.groupMember.create({
          data: { user_id: user.id, group_id: group.id, role: 'MEMBER', total_points: 0 }
        });
      }
    }
    const token = jwt.sign({ id: user.id, email: user.email }, 'MOCK_SECRET');
    res.json({ user, token });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

router.post('/local-login', async (req, res) => {
  try {
    const { email } = req.body;
    const user = await prisma.user.findUnique({ where: { email } });
    if (!user) return res.status(404).json({ error: 'Usuario no encontrado' });
    
    const token = jwt.sign({ id: user.id, email: user.email }, 'MOCK_SECRET');
    res.json({ user, token });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

export default router;
"""

# 2. Update Auth Middleware to verify JWT in mock mode
files["backend/src/middleware/authMiddleware.ts"] = """import { Request, Response, NextFunction } from 'express';
import { PrismaClient } from '@prisma/client';
import * as admin from 'firebase-admin';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
dotenv.config();

const prisma = new PrismaClient();
const useMockAuth = process.env.USE_MOCK_AUTH !== 'false';

let adminInitialized = false;
try {
  if (!useMockAuth && process.env.FIREBASE_SERVICE_ACCOUNT_PATH) {
    const serviceAccount = require('../../firebase-admin.json');
    admin.initializeApp({ credential: admin.credential.cert(serviceAccount) });
    adminInitialized = true;
  }
} catch (e) {
  console.warn("⚠️ No se pudo inicializar Firebase Admin.");
}

export const requireAuth = async (req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split('Bearer ')[1];
  if (!token) return res.status(401).json({ error: 'No token provided' });

  try {
    if (useMockAuth) {
      if (token === 'MOCK_TOKEN') {
        const user = await prisma.user.findFirst({ where: { email: 'alex@test.com' }});
        req.user = user;
        return next();
      }
      
      const decoded: any = jwt.verify(token, 'MOCK_SECRET');
      const user = await prisma.user.findUnique({ where: { id: decoded.id } });
      if (!user) throw new Error('User not found in DB');
      req.user = user;
      return next();
    }

    if (!adminInitialized) throw new Error("Firebase admin not configured");
    const decodedToken = await admin.auth().verifyIdToken(token);
    const user = await prisma.user.findUnique({ where: { email: decodedToken.email } });
    if (!user) return res.status(401).json({ error: 'Unregistered user' });
    
    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};
"""

# 3. Update Frontend AuthContext to call local-register/local-login
files["mobile/src/context/AuthContext.tsx"] = """import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from 'firebase/auth';
import { auth } from '../config/firebase';
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

  const useMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH !== 'false' || auth.app.options.apiKey === 'TU_API_KEY';

  useEffect(() => {
    if (useMockAuth) {
      // Intentar recuperar sesión local
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
      return;
    }

    const unsub = onAuthStateChanged(auth, async (usr) => {
      setUser(usr);
      if (usr) {
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
    if (useMockAuth) {
      const res = await api.post('/auth/local-login', { email: e });
      const mockUser = { uid: res.data.user.id, email: res.data.user.email } as User;
      setUser(mockUser);
      api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
      await AsyncStorage.setItem('mockToken', res.data.token);
      await AsyncStorage.setItem('mockUser', JSON.stringify(mockUser));
      return;
    }
    await signInWithEmailAndPassword(auth, e, p);
  };

  const register = async (e: string, p: string, name: string) => {
    if (useMockAuth) {
      const res = await api.post('/auth/local-register', { email: e, name });
      const mockUser = { uid: res.data.user.id, email: res.data.user.email } as User;
      setUser(mockUser);
      api.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`;
      await AsyncStorage.setItem('mockToken', res.data.token);
      await AsyncStorage.setItem('mockUser', JSON.stringify(mockUser));
      return;
    }
    const cred = await createUserWithEmailAndPassword(auth, e, p);
    const token = await cred.user.getIdToken();
    await api.post('/auth/register', { email: e, name, firebase_uid: cred.user.uid }, {
      headers: { Authorization: `Bearer ${token}` }
    });
  };

  const logout = async () => {
    if (useMockAuth) {
      setUser(null);
      await AsyncStorage.removeItem('mockToken');
      await AsyncStorage.removeItem('mockUser');
      delete api.defaults.headers.common['Authorization'];
      return;
    }
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

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Local Auth with JWT is fully implemented.")
