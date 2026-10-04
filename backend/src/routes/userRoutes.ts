import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/dashboard', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id }, include: { group: true } });
    res.json({
      id: req.user.id, name: req.user.name, reminder_time: req.user.reminder_time,
      totalPoints: member ? member.total_points : 0, streak: member ? member.streak_days : 0,
      groupName: member ? member.group.name : null, groupId: member ? member.group.id : null,
      role: member ? member.role : null, is_on_vacation: member ? member.is_on_vacation : false,
      is_mvp: member ? member.is_mvp : false
    });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/transfer', requireAuth, async (req, res) => {
  try {
    const { to_user_id, amount } = req.body;
    const numAmount = parseInt(amount);
    
    if (numAmount <= 0) return res.status(400).json({ error: 'Cantidad inválida' });

    const fromMember = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!fromMember || fromMember.total_points < numAmount) return res.status(400).json({ error: 'Puntos insuficientes' });

    const toMember = await prisma.groupMember.findFirst({ where: { user_id: to_user_id, group_id: fromMember.group_id } });
    if (!toMember) return res.status(404).json({ error: 'Destinatario no encontrado' });

    await prisma.$transaction([
      prisma.groupMember.update({ where: { id: fromMember.id }, data: { total_points: fromMember.total_points - numAmount } }),
      prisma.groupMember.update({ where: { id: toMember.id }, data: { total_points: toMember.total_points + numAmount } }),
      prisma.pointsLog.create({ data: { user_id: req.user.id, group_id: fromMember.group_id, amount: -numAmount, reason: 'TRANSFER_OUT' } }),
      prisma.pointsLog.create({ data: { user_id: to_user_id, group_id: fromMember.group_id, amount: numAmount, reason: 'TRANSFER_IN' } })
    ]);

    res.json({ success: true, message: `Has transferido ${numAmount} pts a tu compañero.` });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/settings', requireAuth, async (req, res) => {
  try {
    await prisma.user.update({ where: { id: req.user.id }, data: { reminder_time: req.body.reminder_time } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/vacation', requireAuth, async (req, res) => {
  try {
    await prisma.groupMember.updateMany({ where: { user_id: req.user.id }, data: { is_on_vacation: req.body.is_on_vacation } });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
