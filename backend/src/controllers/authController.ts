import { Request, Response } from 'express';
import { authService } from '../services/authService';

export const register = async (req: Request, res: Response) => {
  try {
    const { email, name, firebase_uid } = req.body;
    const user = await authService.registerUser(email, name, firebase_uid);
    res.status(201).json(user);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};

export const login = async (req: Request, res: Response) => {
  try {
    const { firebase_uid } = req.body;
    const user = await authService.loginUser(firebase_uid);
    res.status(200).json(user);
  } catch (error: any) {
    res.status(401).json({ error: error.message });
  }
};
