import os
import re

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/backend/prisma"
schema_path = os.path.join(base_dir, "schema.prisma")

with open(schema_path, "r") as f:
    content = f.read()

if "is_rotational" not in content:
    # Append the fields inside TaskTemplate model
    content = re.sub(r'(model TaskTemplate \{[^}]+frequency\s+String[^}]+)', r'\1\n  is_rotational Boolean @default(false)\n  rotation_index Int @default(0)\n', content)
    
    with open(schema_path, "w") as f:
        f.write(content)
