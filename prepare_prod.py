import os
import json

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. EAS JSON for mobile
files["mobile/eas.json"] = """{
  "cli": {
    "version": ">= 3.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": {
        "buildType": "apk"
      }
    },
    "production": {
      "android": {
        "buildType": "aab"
      }
    }
  },
  "submit": {
    "production": {}
  }
}
"""

# 2. Update app.json
app_json_path = os.path.join(base_dir, "mobile/app.json")
with open(app_json_path, "r", encoding="utf-8") as f:
    app_data = json.load(f)

app_data["expo"]["ios"] = {
    "bundleIdentifier": "com.zutsu.tasker",
    "supportsTablet": True
}
app_data["expo"]["android"] = {
    "package": "com.zutsu.tasker",
    "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#ffffff"
    }
}
files["mobile/app.json"] = json.dumps(app_data, indent=2)


# 3. Backend TSConfig
files["backend/tsconfig.json"] = """{
  "compilerOptions": {
    "target": "es2022",
    "module": "commonjs",
    "rootDir": "./src",
    "outDir": "./dist",
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "**/*.test.ts"]
}
"""

# 4. Update Backend package.json
backend_pkg_path = os.path.join(base_dir, "backend/package.json")
with open(backend_pkg_path, "r", encoding="utf-8") as f:
    pkg_data = json.load(f)

pkg_data["scripts"]["build"] = "tsc"
pkg_data["scripts"]["start"] = "node dist/server.js"
files["backend/package.json"] = json.dumps(pkg_data, indent=2)


# 5. Backend Dockerfile
files["backend/Dockerfile"] = """# Etapa 1: Construcción
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
COPY prisma ./prisma/

# Instalar dependencias
RUN npm ci

COPY . .

# Generar cliente de Prisma y compilar TypeScript
RUN npx prisma generate
RUN npm run build

# Etapa 2: Producción
FROM node:20-alpine

WORKDIR /app

# Copiar archivos compilados y dependencias necesarias
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/prisma ./prisma

# Variables de entorno por defecto
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# El comando de inicio incluye el despliegue automático de migraciones en prod
CMD ["sh", "-c", "npx prisma migrate deploy && npm run start"]
"""

# 6. Backend .dockerignore
files["backend/.dockerignore"] = """node_modules
dist
dev.db
dev.db-journal
.env
firebase-admin.json
*.md
"""

# 7. Render.yaml for easy deployment
files["render.yaml"] = """services:
  - type: web
    name: zutsu-tasker-backend
    env: docker
    dockerContext: ./backend
    dockerfilePath: ./backend/Dockerfile
    envVars:
      - key: PORT
        value: 3000
      - key: DATABASE_URL
        fromDatabase:
          name: zutsu-tasker-db
          property: connectionString
      - key: USE_MOCK_AUTH
        value: false

databases:
  - name: zutsu-tasker-db
    databaseName: zutsu
    user: zutsu_user
    plan: free
"""

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Archivos de producción (EAS, Docker, Render) generados con éxito.")
