import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"

# 1. FIX SCHEMA
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "w") as f:
    f.write("""generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = "file:./dev.db"
}

model User {
  id               String             @id @default(uuid())
  email            String             @unique
  name             String
  created_at       DateTime           @default(now())
  updated_at       DateTime           @updatedAt
  group_members    GroupMember[]
  task_instances   TaskInstance[]     @relation("AssignedUser")
  push_token       String?
  points_logs      PointsLog[]
  reward_redemptions RewardRedemption[]
}

model Group {
  id                 String          @id @default(uuid())
  name               String
  penalty_enabled    Boolean         @default(true)
  penalty_percentage Int             @default(50)
  created_at         DateTime        @default(now())
  updated_at         DateTime        @updatedAt
  members            GroupMember[]
  task_templates     TaskTemplate[]
  task_instances     TaskInstance[]
  rewards            Reward[]
  points_logs        PointsLog[]
}

model GroupMember {
  id           String   @id @default(uuid())
  user_id      String
  group_id     String
  role         String   @default("MEMBER")
  total_points Int      @default(0)
  streak_days  Int      @default(0)
  joined_at    DateTime @default(now())
  user         User     @relation(fields: [user_id], references: [id])
  group        Group    @relation(fields: [group_id], references: [id])

  @@unique([user_id, group_id])
}

model TaskTemplate {
  id             String         @id @default(uuid())
  group_id       String
  title          String
  description    String?        @default("")
  points         Int            @default(10)
  frequency      String         @default("ONCE")
  is_rotational  Boolean        @default(false)
  rotation_index Int            @default(0)
  is_active      Boolean        @default(true)
  group          Group          @relation(fields: [group_id], references: [id])
  instances      TaskInstance[]
}

model TaskInstance {
  id               String       @id @default(uuid())
  template_id      String
  group_id         String
  assigned_to      String?
  due_date         DateTime
  status           String       @default("PENDING")
  points_awarded   Int?
  completed_at     DateTime?
  template         TaskTemplate @relation(fields: [template_id], references: [id])
  group            Group        @relation(fields: [group_id], references: [id])
  assigned_user    User?        @relation("AssignedUser", fields: [assigned_to], references: [id])
}

model Reward {
  id           String             @id @default(uuid())
  group_id     String
  title        String
  cost_points  Int
  yearly_limit Int                @default(1)
  is_active    Boolean            @default(true)
  group        Group              @relation(fields: [group_id], references: [id])
  redemptions  RewardRedemption[]
}

model RewardRedemption {
  id          String   @id @default(uuid())
  reward_id   String
  user_id     String
  redeemed_at DateTime @default(now())
  reward      Reward   @relation(fields: [reward_id], references: [id])
  user        User     @relation(fields: [user_id], references: [id])
}

model PointsLog {
  id         String   @id @default(uuid())
  user_id    String
  group_id   String
  amount     Int
  reason     String
  created_at DateTime @default(now())
  user       User     @relation(fields: [user_id], references: [id])
  group      Group    @relation(fields: [group_id], references: [id])
}
""")

# 2. FIX TASK ROUTES
task_route_path = os.path.join(base_dir, "backend/src/routes/taskRoutes.ts")
with open(task_route_path, "w") as f:
    f.write("""import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { taskService } from '../services/taskService';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    const tasks = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id },
      include: { template: true, assigned_user: true },
      orderBy: { due_date: 'asc' }
    });
    // Transformar para que frontend vea `assigned_to` como objeto {name} en vez de `assigned_user`
    res.json(tasks.map(t => ({...t, assigned_to: t.assigned_user})));
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const { title, description, points, due_date, frequency, assignment_method } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let is_rotational = assignment_method === 'ROTATIONAL';
    let initialAssignee = null;

    if (is_rotational) {
      const allMembers = await prisma.groupMember.findMany({ where: { group_id: member.group_id }, orderBy: { joined_at: 'asc' } });
      if (allMembers.length > 0) initialAssignee = allMembers[0].user_id;
    } else if (assignment_method && assignment_method !== 'ANY') {
      initialAssignee = assignment_method;
    }

    const template = await prisma.taskTemplate.create({
      data: { 
        group_id: member.group_id, 
        title, 
        description: description || '', 
        points: parseInt(points) || 10, 
        frequency: frequency || 'ONCE',
        is_rotational,
        rotation_index: 0
      }
    });

    const instance = await prisma.taskInstance.create({
      data: {
        template_id: template.id,
        group_id: member.group_id,
        due_date: new Date(due_date || new Date()),
        status: 'PENDING',
        assigned_to: initialAssignee
      }
    });

    res.json({ template, instance });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/complete', requireAuth, async (req, res) => {
  try {
    const result = await taskService.completeTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.delete('/:id', requireAuth, async (req, res) => {
  try {
    const task = await prisma.taskInstance.findUnique({ where: { id: req.params.id } });
    if (task) await prisma.taskInstance.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
""")

# 3. FIX TASK SERVICE
task_service_path = os.path.join(base_dir, "backend/src/services/taskService.ts")
with open(task_service_path, "w") as f:
    f.write("""import { PrismaClient } from '@prisma/client';
import { notificationService } from './notificationService';

const prisma = new PrismaClient();

export const taskService = {
  async completeTask(taskId: string, userId: string) {
    const task = await prisma.taskInstance.findUnique({
      where: { id: taskId },
      include: { template: true, group: true }
    });

    if (!task || task.status === 'COMPLETED') throw new Error('Task unavailable');

    const member = await prisma.groupMember.findUnique({
      where: { user_id_group_id: { user_id: userId, group_id: task.group_id } }
    });
    if (!member) throw new Error('Not part of group');

    const now = new Date();
    const isOverdue = now > task.due_date;
    
    let points = task.template.points;
    if (isOverdue && task.group.penalty_enabled) {
      points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
    }

    await prisma.$transaction([
      prisma.taskInstance.update({
        where: { id: taskId },
        data: { status: 'COMPLETED', completed_at: now, assigned_to: userId }
      }),
      prisma.groupMember.update({
        where: { user_id_group_id: { user_id: userId, group_id: task.group_id } },
        data: { total_points: member.total_points + points }
      }),
      prisma.pointsLog.create({
        data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETION' }
      })
    ]);

    const freq = task.template.frequency;
    if (freq && freq !== 'ONCE') {
      const nextDate = new Date(now);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);
      
      let nextAssignee = task.assigned_to;
      
      if (task.template.is_rotational) {
        const members = await prisma.groupMember.findMany({ 
            where: { group_id: task.group_id },
            orderBy: { joined_at: 'asc' } 
        });
        const nextIndex = (task.template.rotation_index + 1) % members.length;
        
        await prisma.taskTemplate.update({
            where: { id: task.template.id },
            data: { rotation_index: nextIndex }
        });
        nextAssignee = members[nextIndex].user_id;
      }

      await prisma.taskInstance.create({
        data: {
          template_id: task.template.id,
          group_id: task.group_id,
          due_date: nextDate,
          status: 'PENDING',
          assigned_to: nextAssignee
        }
      });
    }

    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien completó: ${task.template.title}`, userId);
    return { success: true, message: `Tarea completada, +${points} puntos` };
  }
};
""")
