import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';
import { notificationService } from '../services/notificationService';

const router = Router();
const prisma = new PrismaClient();

router.get('/', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });
    const rewards = await prisma.reward.findMany({ where: { group_id: member.group_id } });
    res.json(rewards);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const { title, cost_points, icon_name, image_uri } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member || member.role !== 'ADMIN') return res.status(403).json({ error: 'Solo los administradores' });
    const reward = await prisma.reward.create({ data: { group_id: member.group_id, title, cost_points: parseInt(cost_points), icon_name: icon_name || 'gift', image_uri: image_uri || null } });
    res.json(reward);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.delete('/:id', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member || member.role !== 'ADMIN') return res.status(403).json({ error: 'Denegado' });
    await prisma.$transaction([
      prisma.rewardRedemption.deleteMany({ where: { reward_id: req.params.id } }),
      prisma.reward.delete({ where: { id: req.params.id } })
    ]);
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/:id/redeem', requireAuth, async (req, res) => {
  try {
    const reward = await prisma.reward.findUnique({ where: { id: req.params.id } });
    if (!reward) return res.status(404).json({ error: 'Reward not found' });
    const member = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: req.user.id, group_id: reward.group_id } } });
    if (!member || member.total_points < reward.cost_points) return res.status(400).json({ error: 'Puntos insuficientes' });

    await prisma.$transaction([
      prisma.groupMember.update({ where: { id: member.id }, data: { total_points: member.total_points - reward.cost_points } }),
      prisma.rewardRedemption.create({ data: { reward_id: reward.id, user_id: req.user.id, status: 'PENDING' } }),
      prisma.pointsLog.create({ data: { user_id: req.user.id, group_id: reward.group_id, amount: -reward.cost_points, reason: 'REWARD_CLAIM' } })
    ]);
    
    await notificationService.notifyGroup(reward.group_id, '🎁 Recompensa Canjeada', `${req.user.name} ha canjeado: ${reward.title}. ¡Pendiente de disfrutar!`, req.user.id);
    res.json({ success: true, message: 'Recompensa canjeada y pendiente de disfrutar' });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});


router.get('/history', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.json([]);
    const history = await prisma.rewardRedemption.findMany({
      where: { reward: { group_id: member.group_id }, status: 'COMPLETED' },
      include: { reward: true, user: true },
      orderBy: { redeemed_at: 'desc' },
      take: 50
    });
    res.json(history);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get('/redemptions', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.json([]);
    const redemptions = await prisma.rewardRedemption.findMany({
      where: { reward: { group_id: member.group_id }, status: 'PENDING' },
      include: { reward: true, user: true },
      orderBy: { redeemed_at: 'desc' }
    });
    res.json(redemptions);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post('/redemptions/:id/complete', requireAuth, async (req, res) => {
  try {
    const redemption = await prisma.rewardRedemption.findUnique({ where: { id: req.params.id }, include: { reward: true } });
    if (!redemption) return res.status(404).json({ error: 'Not found' });
    if (redemption.user_id !== req.user.id) return res.status(403).json({ error: 'Solo puedes dar por completado tu propio canje' });
    
    await prisma.rewardRedemption.update({ where: { id: req.params.id }, data: { status: 'COMPLETED' } });
    await notificationService.notifyGroup(redemption.reward.group_id, '✅ Recompensa Disfrutada', `${req.user.name} por fin ha disfrutado: ${redemption.reward.title}`, req.user.id);
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
