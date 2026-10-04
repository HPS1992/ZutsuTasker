import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

router.get('/equity', requireAuth, async (req, res) => {
  try {
    const user = req.user;
    const member = await prisma.groupMember.findFirst({ where: { user_id: user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    const members = await prisma.groupMember.findMany({
      where: { group_id: member.group_id },
      include: { user: true }
    });

    const totalGroupPoints = members.reduce((acc, m) => acc + m.total_points, 0);

    const stats = members.map(m => ({
      name: m.user.name,
      points: m.total_points,
      percentage: totalGroupPoints === 0 ? 0 : Math.round((m.total_points / totalGroupPoints) * 100)
    }));

    res.json(stats);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
