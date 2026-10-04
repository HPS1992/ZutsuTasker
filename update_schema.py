import os

file_path = "/Volumes/IA_SSD/proyectos/ZutsuTasker/backend/prisma/schema.prisma"

with open(file_path, "r") as f:
    content = f.read()

old_block = """  requires_photo Boolean        @default(false)
  assignment_type String        @default("MANUAL") // RANDOM, MANUAL, FIXED
  fixed_user_id   String?
  is_active       Boolean        @default(true)"""

new_block = """  requires_photo Boolean        @default(false)
  assignment_type String        @default("MANUAL") // RANDOM, MANUAL, FIXED
  fixed_user_id   String?
  icon_name       String?        @default("checkbox")
  image_uri       String?
  room_name       String?        @default("General")
  room_icon       String?        @default("home")
  is_active       Boolean        @default(true)"""

content = content.replace(old_block, new_block)

with open(file_path, "w") as f:
    f.write(content)

print("schema.prisma updated.")
