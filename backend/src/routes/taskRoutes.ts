import { Router } from 'express';
import { requireAuth } from '../middleware/authMiddleware';
import { taskService } from '../services/taskService';
import { PrismaClient } from '@prisma/client';

const router = Router();
const prisma = new PrismaClient();


router.get('/rooms/health', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(404).json({ error: 'No group' });

    const templates = await prisma.taskTemplate.findMany({
      where: { group_id: member.group_id },
      include: { instances: { orderBy: { due_date: 'desc' }, take: 1 } }
    });

    const roomMap = new Map();

    for (const t of templates) {
      const roomName = t.room_name || 'General';
      const roomIcon = t.room_icon || 'home';
      if (!roomMap.has(roomName)) roomMap.set(roomName, { name: roomName, icon: roomIcon, totalHealth: 0, count: 0 });
      
      let tHealth = 100;
      if (t.instances.length > 0) {
        const inst = t.instances[0];
        if (inst.status === 'PENDING') {
          const now = new Date(); now.setHours(0,0,0,0);
          const due = new Date(inst.due_date); due.setHours(0,0,0,0);
          const diffDays = Math.round((due.getTime() - now.getTime()) / 86400000);
          
          if (diffDays >= 2) tHealth = 100;
          else if (diffDays === 1) tHealth = 80;
          else if (diffDays === 0) tHealth = 50;
          else if (diffDays === -1) tHealth = 25;
          else tHealth = 0;
        } else if (inst.status === 'PENDING_REVIEW') {
          tHealth = 90;
        } else if (inst.status === 'COMPLETED') {
          tHealth = 100;
        }
      }
      
      const rm = roomMap.get(roomName);
      rm.totalHealth += tHealth;
      rm.count += 1;
    }

    const rooms = Array.from(roomMap.values()).map((r: any) => ({
      name: r.name,
      icon: r.icon,
      health: Math.round(r.totalHealth / r.count)
    }));

    res.json(rooms);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

router.get('/', requireAuth, async (req, res) => {

  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let tasks = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id },
      include: { template: true, assigned_user: true },
      orderBy: { due_date: 'asc' }
    });
    
    // Inyectar Bounties
    const now = new Date();
    const mappedTasks = tasks.map(t => {
      const dynamicPoints = taskService.calculateBounty(t, t.template.points);
      return {
        ...t, 
        assigned_to: t.assigned_user,
        bounty_points: dynamicPoints > t.template.points ? dynamicPoints : null
      };
    });
    
    res.json(mappedTasks);
  } catch (err: any) { console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); }
});


router.get('/history', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group' });
    const history = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id, status: 'COMPLETED' },
      include: { template: true, assigned_user: true },
      orderBy: { completed_at: 'desc' },
      take: 50 // Limit to last 50 for performance
    });
    res.json(history.map(t => ({...t, assigned_to: t.assigned_user})));
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});

router.post('/', requireAuth, async (req, res) => {
  try {
    const { title, description, points, frequency, assignment_type, fixed_user_id, start_date, end_date, requires_photo, icon_name, image_uri, room_name, room_icon } = req.body;
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group found' });

    let initialAssignee = null;
    if (assignment_type === 'RANDOM') {
      const allMembers = await prisma.groupMember.findMany({ where: { group_id: member.group_id, is_on_vacation: false }, orderBy: { total_points: 'asc' } });
      if (allMembers.length > 0) initialAssignee = allMembers[0].user_id;
    } else if (assignment_type === 'FIXED' && fixed_user_id) initialAssignee = fixed_user_id;

    const template = await prisma.taskTemplate.create({
      data: { 
        group_id: member.group_id, title, description: description || '', points: parseInt(points) || 10, 
        frequency: frequency || 'ONCE', assignment_type: assignment_type || 'MANUAL', 
        fixed_user_id: assignment_type === 'FIXED' ? fixed_user_id : null, 
        start_date: start_date ? new Date(start_date) : new Date(), 
        end_date: end_date ? new Date(end_date) : null,
        requires_photo: !!requires_photo,
        icon_name: icon_name || 'checkbox',
        image_uri: image_uri || null,
        room_name: room_name || 'General',
        room_icon: room_icon || 'home'
      }
    });

    const instance = await prisma.taskInstance.create({
      data: { template_id: template.id, group_id: member.group_id, due_date: template.start_date, status: 'PENDING', assigned_to: initialAssignee }
    });

    res.json({ template, instance });
  } catch (err: any) { console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); }
});

router.post('/:id/complete', requireAuth, async (req, res) => {
  try {
    const { photoUri } = req.body;
    const result = await taskService.completeTask(req.params.id, req.user.id, photoUri);
    res.json(result);
  } catch (err: any) { console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); }
});

router.post('/:id/approve', requireAuth, async (req, res) => {
  try {
    const result = await taskService.approveTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { 
    if (err.message === 'NO_PUEDES_APROBAR_PROPIA') return res.status(400).json({ error: 'No puedes aprobar tu propia foto. Debe hacerlo otro miembro del hogar.' });
    console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); 
  }
});

router.post('/:id/claim', requireAuth, async (req, res) => {
  try {
    const task = await prisma.taskInstance.update({ where: { id: req.params.id }, data: { assigned_to: req.user.id } });
    res.json(task);
  } catch (err: any) { console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); }
});

router.post('/:id/steal', requireAuth, async (req, res) => {
  try {
    const result = await taskService.stealTask(req.params.id, req.user.id);
    res.json(result);
  } catch (err: any) { console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); }
});

router.put('/:id', requireAuth, async (req, res) => {
  try {
    const { id } = req.params;
    const { title, description, points, assignment_type, fixed_user_id, requires_photo, icon_name, room_name, room_icon, due_date } = req.body;
    
    // Buscar la instancia para obtener el template_id
    const instance = await prisma.taskInstance.findUnique({ where: { id } });
    if (!instance) return res.status(404).json({ error: 'Task not found' });

    // Actualizar el template
    await prisma.taskTemplate.update({
      where: { id: instance.template_id },
      data: {
        title,
        description,
        points: points ? parseInt(points) : undefined,
        assignment_type,
        fixed_user_id: assignment_type === 'FIXED' ? fixed_user_id : null,
        requires_photo,
        icon_name,
        room_name,
        room_icon
      }
    });

    // Actualizar la instancia si procede (asignación y fecha límite)
    const updatedInstance = await prisma.taskInstance.update({
      where: { id },
      data: {
        assigned_to: assignment_type === 'FIXED' ? fixed_user_id : instance.assigned_to,
        due_date: due_date ? new Date(due_date) : undefined
      },
      include: { template: true, assigned_user: true }
    });

    res.json(updatedInstance);
  } catch (err: any) {
    console.error("TASK_ROUTE_ERROR", err);
    res.status(500).json({ error: err.message });
  }
});

router.delete('/:id', requireAuth, async (req, res) => {
  try {
    await prisma.taskInstance.delete({ where: { id: req.params.id } });
    res.json({ success: true });
  } catch (err: any) { console.error("TASK_ROUTE_ERROR", err); res.status(500).json({ error: err.message }); }
});

export default router;
