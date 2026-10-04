import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();

// Obtener ajustes del grupo
router.get('/settings', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id }, include: { group: true } });
    if (!member) return res.status(404).json({ error: 'Grupo no encontrado' });
    res.json({ ...member.group, role: member.role });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Guardar ajustes
router.post('/settings', requireAuth, async (req, res) => {
  try {
    const { penalty_enabled, penalty_percentage, name } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id, role: 'ADMIN' } });
    if (!member) return res.status(403).json({ error: 'No tienes permisos de admin' });

    const updated = await prisma.group.update({
      where: { id: member.group_id },
      data: { 
        penalty_enabled: penalty_enabled !== undefined ? penalty_enabled : undefined, 
        penalty_percentage: penalty_percentage !== undefined ? parseInt(penalty_percentage) : undefined,
        name: name !== undefined ? name : undefined
      }
    });
    res.json(updated);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Crear un grupo nuevo
router.post('/create', requireAuth, async (req, res) => {
  try {
    const { name } = req.body;
    const group = await prisma.group.create({ data: { name } });
    await prisma.groupMember.create({
      data: { user_id: req.user.id, group_id: group.id, role: 'ADMIN', total_points: 0 }
    });
    res.json(group);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Unirse a un grupo mediante ID
router.post('/join', requireAuth, async (req, res) => {
  try {
    const { groupId } = req.body;
    const group = await prisma.group.findUnique({ where: { id: groupId } });
    if (!group) return res.status(404).json({ error: 'Código de grupo inválido' });

    await prisma.groupMember.create({
      data: { user_id: req.user.id, group_id: group.id, role: 'MEMBER', total_points: 0 }
    });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Listar miembros
router.get('/members', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(404).json({ error: 'No estás en un grupo' });

    const members = await prisma.groupMember.findMany({
      where: { group_id: member.group_id },
      include: { user: true }
    });
    res.json(members.map(m => ({ id: m.user.id, name: m.user.name, role: m.role, points: m.total_points })));
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

// Expulsar miembro
router.delete('/members/:userId', requireAuth, async (req, res) => {
  try {
    const adminMember = await prisma.groupMember.findFirst({ where: { user_id: req.user.id, role: 'ADMIN' } });
    if (!adminMember) return res.status(403).json({ error: 'No tienes permisos de admin' });

    await prisma.groupMember.delete({
      where: { user_id_group_id: { user_id: req.params.userId, group_id: adminMember.group_id } }
    });
    res.json({ success: true });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
