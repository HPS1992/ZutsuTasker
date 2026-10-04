# Etapa 1: Construcción
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
