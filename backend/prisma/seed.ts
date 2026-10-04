import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('Iniciando seed de datos falsos...');

  // 1. Crear usuarios
  const user1 = await prisma.user.create({ data: { email: 'alex@test.com', name: 'Álex' } });
  const user2 = await prisma.user.create({ data: { email: 'maria@test.com', name: 'María' } });
  const user3 = await prisma.user.create({ data: { email: 'carlos@test.com', name: 'Carlos' } });

  // 2. Crear Grupo
  const group = await prisma.group.create({
    data: { name: 'Piso Estudiantes' }
  });

  // 3. Asociar miembros al grupo
  await prisma.groupMember.createMany({
    data: [
      { user_id: user1.id, group_id: group.id, role: 'ADMIN', total_points: 120 },
      { user_id: user2.id, group_id: group.id, role: 'MEMBER', total_points: 95 },
      { user_id: user3.id, group_id: group.id, role: 'MEMBER', total_points: 40 },
    ]
  });

  // 4. Crear Plantillas de tareas
  const template1 = await prisma.taskTemplate.create({
    data: { group_id: group.id, title: 'Bajar basura', category: 'Cocina', duration_min: 5, complexity: 1, base_points: 10 }
  });
  const template2 = await prisma.taskTemplate.create({
    data: { group_id: group.id, title: 'Limpiar Baño', category: 'Limpieza', duration_min: 30, complexity: 3, base_points: 50 }
  });

  // 5. Crear Instancias de Tareas (asignadas y sin asignar)
  await prisma.taskInstance.create({
    data: { template_id: template1.id, group_id: group.id, assigned_to: user1.id, due_date: new Date(), status: 'PENDING' }
  });
  await prisma.taskInstance.create({
    data: { template_id: template2.id, group_id: group.id, assigned_to: user2.id, due_date: new Date(), status: 'COMPLETED', completed_at: new Date(), points_awarded: 50 }
  });

  // 6. Crear Recompensas en el Market
  await prisma.reward.create({
    data: { group_id: group.id, title: 'Librarse de fregar', cost_points: 100, yearly_limit: 5 }
  });
  await prisma.reward.create({
    data: { group_id: group.id, title: 'Cena pagada por los demás', cost_points: 1000, yearly_limit: 1 }
  });

  console.log('Seed finalizado con éxito. Grupo, Usuarios, Tareas y Recompensas creados.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
