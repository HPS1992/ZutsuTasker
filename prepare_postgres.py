import os

file_path = "/Volumes/IA_SSD/proyectos/ZutsuTasker/backend/prisma/schema.prisma"

with open(file_path, "r") as f:
    content = f.read()

content = content.replace('provider = "sqlite"', 'provider = "postgresql"')
content = content.replace('url      = "file:./dev.db"', 'url      = env("DATABASE_URL")')

with open(file_path, "w") as f:
    f.write(content)

print("schema.prisma updated for PostgreSQL.")
