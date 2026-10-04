import os

file_path = "/Volumes/IA_SSD/proyectos/ZutsuTasker/backend/prisma/schema.prisma"

with open(file_path, "r") as f:
    content = f.read()

old_user = """model User {
  id               String             @id @default(uuid())
  email            String             @unique
  name             String
  created_at       DateTime           @default(now())"""

new_user = """model User {
  id               String             @id @default(uuid())
  email            String             @unique
  password         String             @default("")
  name             String
  created_at       DateTime           @default(now())"""

content = content.replace(old_user, new_user)

with open(file_path, "w") as f:
    f.write(content)

print("Added password field to User model.")
