import { Request, Response } from 'express';
import { taskService } from '../services/taskService';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export const listTasks = async (req: Request, res: Response) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });
    
    const tasks = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id },
      include: { template: true, assigned_user: true },
      orderBy: { due_date: 'asc' }
    });
    const response = tasks.map(task => ({
      ...task,
      assigned_to: task.assigned_user,
      bounty_points: taskService.calculateBounty(task, task.template.points)
    }));
    res.status(200).json(response);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
};

export const createTask = async (req: Request, res: Response) => {
  try {
    const user = req.user;
    const { title, points, due_date } = req.body;
    
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    // En vez de usar un template real, creamos uno al vuelo (simplificación para MVP)
    const template = await prisma.taskTemplate.create({
      data: {
        group_id: member.group_id,
        title,
        points: parseInt(points) || 20
      }
    });

    const newTask = await prisma.taskInstance.create({
      data: {
        template_id: template.id,
        group_id: member.group_id,
        due_date: due_date ? new Date(due_date) : new Date(),
        status: 'PENDING'
      }
    });

    res.status(201).json(newTask);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};

export const completeTask = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const user = req.user;
    const result = await taskService.completeTask(id, user.id);
    res.status(200).json(result);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
};
