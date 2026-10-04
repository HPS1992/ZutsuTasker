import os

file_path = "/Volumes/IA_SSD/proyectos/ZutsuTasker/backend/src/routes/taskRoutes.ts"

with open(file_path, "r") as f:
    content = f.read()

old_req = "const { title, description, points, frequency, assignment_type, fixed_user_id, start_date, end_date, requires_photo } = req.body;"
new_req = "const { title, description, points, frequency, assignment_type, fixed_user_id, start_date, end_date, requires_photo, icon_name, image_uri, room_name, room_icon } = req.body;"

old_data = """      data: { 
        group_id: member.group_id, title, description: description || '', points: parseInt(points) || 10, 
        frequency: frequency || 'ONCE', assignment_type: assignment_type || 'MANUAL', 
        fixed_user_id: assignment_type === 'FIXED' ? fixed_user_id : null, 
        start_date: start_date ? new Date(start_date) : new Date(), 
        end_date: end_date ? new Date(end_date) : null,
        requires_photo: !!requires_photo
      }"""

new_data = """      data: { 
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
      }"""

content = content.replace(old_req, new_req).replace(old_data, new_data)

with open(file_path, "w") as f:
    f.write(content)

print("taskRoutes updated with icon, image and room fields.")
