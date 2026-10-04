# Zutsu Tasker 🚀

Zutsu Tasker es una aplicación móvil gamificada diseñada para resolver la gestión de tareas domésticas en entornos compartidos (pisos de estudiantes, parejas, familias). Aplica el concepto japonés de "cada uno su parte" (ずつ) para garantizar la **equidad y transparencia**.

## ✨ Efectos WOW y Características Clave

1. **Gamificación y Recompensas (Marketplace)**: Las tareas otorgan puntos basados en duración y complejidad. Los puntos se canjean por recompensas personalizadas (ej. "Librarse de fregar" o "Cena pagada").
2. **Sistema de Equidad Transparente**: Visualización clara del % de aportación de cada integrante. El líder del mes destaca con diseño dorado.
3. **Penalizaciones automáticas (Overdue)**: Si una tarea se retrasa más de 2 días, la app activa la penalización (por defecto -50% de los puntos) y rompe la racha del usuario, fomentando la disciplina.
4. **Animaciones de Recompensa**: Lluvia de confeti al completar tareas (efecto de dopamina visual) y componentes Glassmorphism UI.
5. **Autenticación Escalable**: Preparado para Firebase Auth (Email/SSO) y sincronizado con base de datos propia para control total.

## 🛠️ Stack Tecnológico

- **Frontend**: React Native + Expo + TypeScript + React Navigation.
- **Backend**: Node.js + Express + TypeScript + Prisma ORM.
- **Base de datos**: SQLite (Fácil de migrar a PostgreSQL).
- **Despliegue recomendado**: Frontend en Vercel/Expo Application Services (EAS). Backend en Render/Railway.

## 🚀 Instrucciones de Arranque

### 1. Backend
```bash
cd backend
npm install
npx prisma db push      # Sincroniza esquema de base de datos
npx prisma db seed      # Carga datos de prueba (Alex, Maria, Carlos)
npm run dev             # Inicia el servidor en http://localhost:3000
```

### 2. Frontend
```bash
cd mobile
npm install
npx expo start          # Inicia el Metro Bundler
```
Escanea el código QR con Expo Go en tu móvil, o pulsa `w` para verlo en tu navegador.

*Nota:* Si pruebas en móvil real, asegúrate de actualizar `mobile/src/services/api.ts` con la IP local de tu ordenador en lugar de `localhost`, o usa el túnel de Expo.

## 👥 Datos de Prueba (Seed)

El seed genera:
- **Grupo**: Piso Estudiantes
- **Usuarios**: Alex, Maria, Carlos
- **Tareas**: Limpiar Baño (Pendiente), Bajar basura (Completada).
- **Market**: "Librarse de fregar" (100pts), "Cena pagada" (1000pts).

Inicia sesión con cualquier email (ej: `alex@test.com`) y el sistema te dará paso automático con el perfil de pruebas.
