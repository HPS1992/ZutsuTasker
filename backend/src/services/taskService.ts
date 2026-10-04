import { PrismaClient } from '@prisma/client';
import { notificationService } from './notificationService';

const prisma = new PrismaClient();

export const taskService = {
  // Helpers
  calculateBounty(task: any, basePoints: number) {
    if (task.template.assignment_type === 'MANUAL' && !task.assigned_to) {
      const daysOld = Math.floor((new Date().getTime() - task.created_at.getTime()) / (1000 * 3600 * 24));
      if (daysOld > 0) return basePoints + (daysOld * 5); // +5 puntos por cada día ignorada
    }
    return basePoints;
  },

  async updateStreakAndMVP(groupId: string, userId: string) {
    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: userId, group_id: groupId } } });
    if (!member) return;
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    let newStreak = member.streak_days;
    if (member.last_completed_date) {
      const last = new Date(member.last_completed_date);
      const lastDay = new Date(last.getFullYear(), last.getMonth(), last.getDate());
      const diffDays = Math.floor((today.getTime() - lastDay.getTime()) / (1000 * 3600 * 24));
      
      if (diffDays === 1) newStreak += 1;
      else if (diffDays > 1) newStreak = 1;
    } else {
      newStreak = 1;
    }

    await prisma.groupMember.update({
      where: { id: member.id },
      data: { streak_days: newStreak, last_completed_date: now }
    });

    // Calcular MVP semanal (Lógica simple: el que más puntos tenga en total, 
    // en un caso real se filtra por los puntos de los últimos 7 días)
    const members = await prisma.groupMember.findMany({
      where: { group_id: groupId },
      orderBy: { total_points: 'desc' }
    });
    
    if (members.length > 0) {
      // Limpiar MVP anterior
      await prisma.groupMember.updateMany({ where: { group_id: groupId }, data: { is_mvp: false } });
      // Coronar nuevo MVP
      await prisma.groupMember.update({ where: { id: members[0].id }, data: { is_mvp: true } });
    }
  },

  async completeTask(taskId: string, userId: string, photoUri?: string) {
    const task = await prisma.taskInstance.findUnique({ where: { id: taskId }, include: { template: true, group: true } });
    if (!task || task.status === 'COMPLETED' || task.status === 'PENDING_REVIEW') throw new Error('Task unavailable');

    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } } });
    if (!member) throw new Error('Not part of group');

    if (task.template.requires_photo && !photoUri) {
      throw new Error('Esta tarea requiere foto obligatoria');
    }

    if (task.template.requires_photo && photoUri) {
      await prisma.taskInstance.update({
        where: { id: taskId },
        data: { status: 'PENDING_REVIEW', photo_uri: photoUri, assigned_to: userId }
      });
      await notificationService.notifyGroup(task.group_id, '📸 Foto a revisión', `Alguien ha subido foto para: ${task.template.title}`, userId);
      return { success: true, message: 'Foto enviada. Esperando aprobación de los compañeros.' };
    }

    // Flujo normal sin foto
    const now = new Date();
    const isOverdue = now > task.due_date;
    
    let points = this.calculateBounty(task, task.template.points);
    
    let penaltyApplied = false;
    if (isOverdue && task.group.penalty_enabled && task.assigned_to) {
        const originalAssignee = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
        if (originalAssignee && !originalAssignee.is_on_vacation) {
            points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
            penaltyApplied = true;
        }
    }

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, assigned_to: userId, points_awarded: points, penalty_applied: penaltyApplied } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: userId, group_id: task.group_id } }, data: { total_points: member.total_points + points } }),
      prisma.pointsLog.create({ data: { user_id: userId, group_id: task.group_id, amount: points, reason: 'TASK_COMPLETION' } })
    ]);

    await this.updateStreakAndMVP(task.group_id, userId);
    await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);
    await notificationService.notifyGroup(task.group_id, '✅ Tarea completada', `Alguien completó: ${task.template.title}`, userId);
    return { success: true, message: `Tarea completada, +${points} puntos` };
  },

  async approveTask(taskId: string, approverId: string) {
    const task = await prisma.taskInstance.findUnique({ where: { id: taskId }, include: { template: true, group: true } });
    if (!task || task.status !== 'PENDING_REVIEW' || !task.assigned_to) throw new Error('Invalid task');
    if (task.assigned_to === approverId) throw new Error('NO_PUEDES_APROBAR_PROPIA');

    const points = this.calculateBounty(task, task.template.points);
    const now = new Date();
    
    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, points_awarded: points } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } }, data: { total_points: (member?.total_points || 0) + points } }),
      prisma.pointsLog.create({ data: { user_id: task.assigned_to, group_id: task.group_id, amount: points, reason: 'TASK_APPROVED' } })
    ]);

    await this.updateStreakAndMVP(task.group_id, task.assigned_to);
    await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);
    await notificationService.notifyGroup(task.group_id, '🎉 Foto Aprobada', `Se han liberado los puntos de: ${task.template.title}`, approverId);
    return { success: true, message: 'Foto aprobada y puntos entregados' };
  },

  async stealTask(taskId: string, thiefId: string) {
    const task = await prisma.taskInstance.findUnique({ where: { id: taskId }, include: { template: true, group: true } });
    if (!task || task.status === 'COMPLETED' || task.status === 'PENDING_REVIEW') throw new Error('Task unavailable');
    if (!task.assigned_to || task.assigned_to === thiefId) throw new Error('No puedes robar esta tarea');

    const victimMember = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
    if (victimMember?.is_on_vacation) throw new Error('No puedes robarle tareas a alguien en modo vacaciones');

    const now = new Date();
    const daysOverdue = (now.getTime() - task.due_date.getTime()) / (1000 * 3600 * 24);

    if (daysOverdue < 0 || daysOverdue > 2) throw new Error('Solo puedes robar tareas vencidas hace menos de 2 días');

    const basePoints = task.template.points;
    const stolenReward = Math.floor(basePoints * 1.5);
    const stolenPenalty = Math.floor(basePoints * 0.5);

    const thiefMember = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: thiefId, group_id: task.group_id } } });
    if (!thiefMember || !victimMember) throw new Error('Group error');

    await prisma.$transaction([
      prisma.taskInstance.update({ where: { id: taskId }, data: { status: 'COMPLETED', completed_at: now, assigned_to: thiefId, is_stolen: true, penalty_applied: true, points_awarded: stolenReward } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: thiefId, group_id: task.group_id } }, data: { total_points: thiefMember.total_points + stolenReward } }),
      prisma.pointsLog.create({ data: { user_id: thiefId, group_id: task.group_id, amount: stolenReward, reason: 'TASK_STOLEN_REWARD' } }),
      prisma.groupMember.update({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } }, data: { total_points: victimMember.total_points - stolenPenalty } }),
      prisma.pointsLog.create({ data: { user_id: task.assigned_to, group_id: task.group_id, amount: -stolenPenalty, reason: 'TASK_STOLEN_PENALTY' } })
    ]);

    await this.updateStreakAndMVP(task.group_id, thiefId);
    await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);
    await notificationService.notifyGroup(task.group_id, '🥷 ¡Tarea robada!', `Alguien ha robado: ${task.template.title}`, thiefId);
    return { success: true, message: `¡Tarea robada! +${stolenReward} pts para ti, -${stolenPenalty} pts para la víctima.` };
  },

  async spawnNextInstance(template: any, groupId: string, now: Date, originalDueDate: Date) {
    const freq = template.frequency;
    if (freq && freq !== 'ONCE') {
      const baseDate = originalDueDate > now ? originalDueDate : now;
      const nextDate = new Date(baseDate);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'BIWEEKLY') nextDate.setDate(nextDate.getDate() + 14);
      else if (freq === 'BIMONTHLY') nextDate.setMonth(nextDate.getMonth() + 2);
      else if (freq === 'QUARTERLY') nextDate.setMonth(nextDate.getMonth() + 3);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);
      
      if (template.end_date && nextDate > new Date(template.end_date)) return;

      let nextAssignee = null;
      if (template.assignment_type === 'RANDOM') {
        const members = await prisma.groupMember.findMany({ where: { group_id: groupId, is_on_vacation: false }, orderBy: { total_points: 'asc' } });
        if (members.length > 0) nextAssignee = members[0].user_id;
      } else if (template.assignment_type === 'FIXED') {
        nextAssignee = template.fixed_user_id;
      }

      await prisma.taskInstance.create({
        data: { template_id: template.id, group_id: groupId, due_date: nextDate, status: 'PENDING', assigned_to: nextAssignee }
      });
    }
  }
};
