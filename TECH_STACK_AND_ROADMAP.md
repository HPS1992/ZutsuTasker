# Zutsu Tasker - Guía de Inicio Rápido y Arquitectura

## 1. Stack Tecnológico Seleccionado
*   **Frontend Móvil:** **React Native con Expo**. Justificación: Permite iterar rapidísimo, compartir código al 100% entre iOS y Android, y facilita el acceso a APIs nativas sin configuraciones complejas iniciales.
*   **Backend:** **Node.js con Express y TypeScript**. Justificación: Ligero, gran ecosistema, el equipo puede usar TypeScript en todo el stack (Full-Stack TS), reduciendo la fricción mental de cambiar de lenguaje.
*   **Base de Datos:** **PostgreSQL** (gestionado vía **Prisma ORM**). Justificación: El modelo de Zutsu es altamente relacional (usuarios -> grupos -> tareas -> historiales de puntos). PostgreSQL asegura integridad referencial y Prisma da un tipado estricto espectacular.
*   **Autenticación:** **Firebase Auth**. Justificación: Implementación de SSO (Google/Apple) trivial en móviles, gestión segura de sesiones, y tokens JWT fáciles de verificar en nuestro backend Node.
*   **Notificaciones Push:** **Expo Push Notifications**. Justificación: Ya viene integrado con Expo, abstrayendo la complejidad enorme de APNs (Apple) y FCM (Android).

## 2. Estructura de Carpetas Frontend (React Native + Expo)
```
mobile/
├── App.tsx                 # Punto de entrada y configuración de navegación raíz
├── app.json                # Configuración de Expo
├── src/
│   ├── assets/             # Imágenes, iconos, fuentes locales
│   ├── components/         # Componentes UI reutilizables (Botones, Tarjetas, Modales)
│   ├── config/             # Variables de entorno, constantes, temas (colores)
│   ├── hooks/              # Custom hooks (ej. useAuth, useTasks)
│   ├── navigation/         # Definición de Stacks y Tabs de React Navigation
│   ├── screens/            # Pantallas completas (Home, Login, Tareas)
│   ├── services/           # Llamadas a la API backend (axios/fetch), integración Firebase
│   ├── store/              # Estado global (Zustand o Context API)
│   └── utils/              # Funciones helper (formateo de fechas, cálculo de puntos local)
```

## 3. Modelo de Datos Concreto (PostgreSQL + Prisma)
Ver archivo `backend/prisma/schema.prisma` para la definición exacta. Entidades principales:
*   `User`: id, email, name.
*   `Group`: id, name.
*   `GroupMember`: une usuario y grupo con su rol y puntos actuales.
*   `TaskTemplate`: base de las tareas. Define la complejidad y puntos base.
*   `TaskInstance`: la tarea concreta asignada a una fecha y un usuario. status, points_awarded.
*   `PointsLog`: registro inmutable de cada ganancia/pérdida de puntos para auditoría y gráficas.
*   `Reward` / `RewardRedemption`: catálogo y registro de canjes.

## 4. Instrucciones de Puesta en Marcha

### Backend
1. `cd backend`
2. Inicializa el proyecto: `npm init -y`
3. Instala dependencias: `npm i express cors dotenv prisma @prisma/client`
4. Dependencias de desarrollo: `npm i -D typescript @types/express @types/node @types/cors ts-node-dev`
5. Inicializa TypeScript: `npx tsc --init`
6. Levanta una base de datos PostgreSQL local (ej. vía Docker: `docker run --name zutsu-db -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres`)
7. Configura el `.env` en backend: `DATABASE_URL="postgresql://postgres:postgres@localhost:5432/zutsu?schema=public"`
8. Sincroniza la BD: `npx prisma db push`
9. Inserta datos de prueba: `npx prisma db seed` (requiere configurar ts-node en package.json)
10. Corre el server: `npm run dev` (usando ts-node-dev src/server.ts)

### Frontend
1. `cd mobile`
2. Si no lo has hecho, inicializa expo: `npx create-expo-app . -t expo-template-blank-typescript`
3. Instala dependencias de navegación: `npm install @react-navigation/native @react-navigation/native-stack @react-navigation/bottom-tabs react-native-screens react-native-safe-area-context`
4. Levanta el emulador o app: `npm start` (abre Expo Go en tu móvil o simulador)

## 5. Hoja de Ruta Sugerida (Próximas iteraciones)

*   **Iteración 1: Core Foundation.** 
    *   Setup de Firebase Auth.
    *   Creación de Grupos e Invitaciones.
    *   Listado básico de tareas consumiendo la API.
*   **Iteración 2: Motor de Tareas.** 
    *   Creación de tareas (templates y asignaciones).
    *   Endpoint para completar tareas de forma transaccional.
    *   Suma de puntos reflejada en la Home.
*   **Iteración 3: Gamificación & Market.** 
    *   Creación visual del Market.
    *   Lógica de descuento de puntos al canjear.
    *   Penalizaciones automáticas por retraso (Cron Job en backend).
*   **Iteración 4: Rotación y Equidad.** 
    *   Implementación del algoritmo de rotación automática.
    *   Gráficos visuales de equidad en la vista de Estadísticas.
*   **Iteración 5: Refinamiento.** 
    *   Expo Push Notifications.
    *   Calendario interactivo (react-native-calendars).
    *   Pulido de animaciones y microinteracciones (Lottie/Reanimated).
