import { Request, Response, NextFunction } from 'express';
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
