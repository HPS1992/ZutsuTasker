import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/backend"
file_path = os.path.join(base_dir, "src/services/taskService.ts")

with open(file_path, "r") as f:
    content = f.read()

# Fix the completeTask function
old_block = """    if (isOverdue && task.group.penalty_enabled && task.assigned_to) {
        const originalAssignee = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
        if (originalAssignee && !originalAssignee.is_on_vacation) {
            points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
        }
    }"""

new_block = """    let penaltyApplied = false;
    if (isOverdue && task.group.penalty_enabled && task.assigned_to) {
        const originalAssignee = await prisma.groupMember.findUnique({ where: { user_id_group_id: { user_id: task.assigned_to, group_id: task.group_id } } });
        if (originalAssignee && !originalAssignee.is_on_vacation) {
            points = Math.floor(points * (1 - task.group.penalty_percentage / 100));
            penaltyApplied = true;
        }
    }"""

content = content.replace(old_block, new_block)

# Fix the handleComplete missing try/catch in frontend as well to show errors
ts_path = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile/src/screens/TasksScreen.tsx"
with open(ts_path, "r") as f:
    ts_content = f.read()

old_handle = """  const handleComplete = async (item: any) => {
    if (item.template.requires_photo) {
      let result = await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5 });
      if (!result.canceled && result.assets[0].uri) {
        await completeTask(item.id, result.assets[0].uri); fetchRooms();
      }
    } else {
      setShowConfetti(false);
      await completeTask(item.id);
      fetchRooms();
      setShowConfetti(true);
    }
  };"""

new_handle = """  const handleComplete = async (item: any) => {
    try {
      if (item.template.requires_photo) {
        let result = await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5 });
        if (!result.canceled && result.assets[0].uri) {
          await completeTask(item.id, result.assets[0].uri); fetchRooms();
        }
      } else {
        setShowConfetti(false);
        await completeTask(item.id);
        fetchRooms();
        setShowConfetti(true);
      }
    } catch(e: any) { alert('Error: ' + (e.response?.data?.error || e.message)); }
  };"""

ts_content = ts_content.replace(old_handle, new_handle)

with open(file_path, "w") as f:
    f.write(content)

with open(ts_path, "w") as f:
    f.write(ts_content)

print("Backend reference error fixed.")
