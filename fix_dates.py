import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"

# 1. Update Frontend TasksScreen.tsx to NOT offset the initial due_date
screen_path = os.path.join(base_dir, "mobile/src/screens/TasksScreen.tsx")
with open(screen_path, "r") as f:
    content = f.read()

# Replace the incorrect logic
old_logic = """const due = new Date();
    if (freq === 'DAILY') due.setDate(due.getDate() + 1);
    else if (freq === 'WEEKLY') due.setDate(due.getDate() + 7);
    else if (freq === 'MONTHLY') due.setMonth(due.getMonth() + 1);"""

new_logic = """const due = new Date(); // La primera vez siempre es para hoy"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open(screen_path, "w") as f:
        f.write(content)

# 2. Update Backend taskService.ts to calculate nextDate based on task's due_date
service_path = os.path.join(base_dir, "backend/src/services/taskService.ts")
with open(service_path, "r") as f:
    service_content = f.read()

old_spawn_call = "await this.spawnNextInstance(task.template, task.group_id, now);"
new_spawn_call = "await this.spawnNextInstance(task.template, task.group_id, now, task.due_date);"

old_spawn_def = "async spawnNextInstance(template: any, groupId: string, now: Date) {"
new_spawn_def = "async spawnNextInstance(template: any, groupId: string, now: Date, originalDueDate: Date) {"

old_spawn_logic = """const nextDate = new Date(now);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);"""

new_spawn_logic = """// Si se completa por adelantado, sumamos desde la fecha original. 
      // Si se completa con retraso, sumamos desde hoy para no generar tareas en el pasado.
      const baseDate = originalDueDate > now ? originalDueDate : now;
      const nextDate = new Date(baseDate);
      if (freq === 'DAILY') nextDate.setDate(nextDate.getDate() + 1);
      else if (freq === 'WEEKLY') nextDate.setDate(nextDate.getDate() + 7);
      else if (freq === 'MONTHLY') nextDate.setMonth(nextDate.getMonth() + 1);"""

if old_spawn_call in service_content:
    service_content = service_content.replace(old_spawn_call, new_spawn_call)
    service_content = service_content.replace(old_spawn_def, new_spawn_def)
    service_content = service_content.replace(old_spawn_logic, new_spawn_logic)
    
    with open(service_path, "w") as f:
        f.write(service_content)

print("Bug de duplicación de tareas corregido.")
