# Zutsu Tasker - Especificación Funcional y Técnica

## 1. Visión y Objetivos del Producto

**Zutsu Tasker** nace con el propósito de resolver uno de los problemas más comunes en la convivencia: el reparto desigual de las responsabilidades domésticas. Inspirado en el concepto japonés "Zutsu" (ずつ - cada uno su parte), la aplicación busca transformar las tareas del hogar, tradicionalmente vistas como una carga, en una experiencia gamificada, justa y transparente.

**Objetivos clave:**
- **Fomentar la equidad:** Visibilizar quién hace qué mediante métricas claras y un sistema de puntos objetivo.
- **Reducir la fricción:** Automatizar y facilitar la asignación y el seguimiento de tareas para evitar discusiones.
- **Motivar a través del juego:** Recompensar el esfuerzo mediante logros, rachas y un "Market de Recompensas" interno.
- **Adaptabilidad:** Ser útil tanto para parejas como para familias con adolescentes o pisos de estudiantes.

---

## 2. Descripción de Funcionalidades y Flujos de Usuario

### 2.1. Gestión de Usuarios y Grupos
- **Registro/Login:** Email, teléfono, Google, Apple.
- **Creación de Grupo:** Un usuario crea un "Hogar" y se convierte en Administrador. Se genera un código/link de invitación.
- **Roles:** 
  - *Admin:* Puede modificar reglas, tareas base, recompensas y penalizaciones.
  - *Miembro:* Puede completar tareas, canjear recompensas y crear tareas personales.
- **Multi-grupo:** Un usuario puede cambiar entre diferentes hogares (ej. Casa familiar vs. Piso de universidad).

### 2.2. Catálogo y Gestión de Tareas
- **Categorías:** Limpieza, Cocina, Mascotas, Organización, Mantenimiento, Compras.
- **Propiedades de Tarea:** Nombre, descripción, icono, duración estimada (min), complejidad (1-Baja, 2-Media, 3-Alta).
- **Tipos de Asignación:**
  - *Puntuales:* Una sola vez.
  - *Recurrentes:* Diarias, semanales, "cada 3 días", "segundos domingos".
- **Modos de Reparto:**
  - *Manual:* El admin asigna, o los miembros "rescatan" de un backlog (tablero de disponibles).
  - *Rotación Automática:* La app cambia de responsable en cada ciclo (ej. la basura rota cada semana).
  - *Asignación Inteligente:* La app balancea la carga según los puntos acumulados en el mes para mantener la equidad.

### 2.3. Sistema de Puntos, Penalizaciones y Equidad
- **Cálculo Base:** `Puntos = (Duración × Factor_Tiempo) + (Complejidad × Factor_Complejidad)`.
- **Penalizaciones:** Si una tarea vence y pasan 2 días sin completarse, se resta una cantidad (configurable: 50%, 100% o 200% del valor de la tarea).
- **Equidad:** La app muestra un "Semáforo de Equilibrio" o gráfico de pastel que indica el % de carga de cada usuario en el mes en curso respecto al total.

### 2.4. Market de Recompensas
- **Concepto:** Los puntos sirven como moneda de cambio para reclamar premios que el resto del grupo debe cumplir o facilitar.
- **Configuración:** El Admin define el catálogo (Ej: "Cena pagada" = 500 pts, límite 1/año; "Librarse de fregar hoy" = 50 pts).
- **Flujo de Canje:** El usuario selecciona la recompensa, se descuentan los puntos (registrado en histórico) y se notifica al grupo para su cumplimiento.

### 2.5. Calendario y Recordatorios
- **Vistas:** Mensual y semanal (personal y grupal).
- **Notificaciones:** Push parametrizables (día antes, misma mañana, etc.) y resúmenes semanales ("¡Esta semana hiciste un 40% de las tareas!").

---

## 3. Propuesta de Modelo de Datos (Relacional / Documental)

A continuación, una abstracción del esquema de datos:

- **User**
  - `id` (UUID), `name`, `email`, `avatar_url`, `created_at`
- **Group**
  - `id`, `name`, `admin_id`, `points_rules` (JSON), `penalty_rules` (JSON)
- **GroupMember**
  - `group_id`, `user_id`, `role` (admin/member), `total_points`, `monthly_points`, `streak_days`
- **TaskTemplate** (Plantillas de tareas)
  - `id`, `group_id`, `title`, `description`, `category`, `icon`, `duration_min`, `complexity`, `base_points`, `is_active`
- **TaskInstance** (Instancias reales a realizar)
  - `id`, `template_id`, `group_id`, `assigned_to` (user_id), `due_date`, `status` (pending/completed/expired), `completed_at`, `points_awarded`, `penalty_applied`
- **TaskRecurrence** (Reglas de repetición)
  - `id`, `template_id`, `pattern` (cron o JSON), `rotation_logic`
- **Reward**
  - `id`, `group_id`, `title`, `description`, `cost_points`, `yearly_limit`, `icon`
- **RewardRedemption** (Historial de canjes)
  - `id`, `reward_id`, `user_id`, `redeemed_at`
- **PointsLog** (Auditoría de puntos para históricos)
  - `id`, `user_id`, `group_id`, `amount` (+/-), `reason` (task_completed, penalty, reward_claimed), `reference_id`, `timestamp`

---

## 4. Esquema de Pantallas (UI/UX)

1. **Onboarding & Auth:**
   - Carrusel de beneficios, Login/Registro, Flujo de unirse con código o crear nuevo hogar.
2. **Home (Dashboard Personal):**
   - Resumen rápido: Mis puntos, racha actual, % de equidad.
   - Carrusel horizontal: "Mis tareas para hoy/mañana".
   - Botón flotante (FAB): "Nueva Tarea" o "Registrar acción".
3. **Listado de Tareas (Backlog):**
   - Pestañas: *Mis tareas* | *Disponibles (sin asignar)* | *Todas*.
   - Filtros por categoría y estado.
4. **Detalle de Tarea:**
   - Info de la tarea, botón gigante para "Marcar Completada", opciones para reasignar o editar.
5. **Calendario:**
   - Vista clásica de mes con puntos/iconos en días con tareas. Al tocar un día, lista inferior de tareas.
6. **Market de Recompensas:**
   - Tarjetas visuales con las recompensas, indicando coste y mis puntos disponibles. Botón "Canjear".
7. **Estadísticas (Grupal):**
   - Ranking del mes, gráfico de distribución del peso del hogar, histórico de canjes.
8. **Perfil / Ajustes de Grupo:**
   - Gestión de miembros, edición del catálogo base de tareas, configuración de la fórmula de puntos y reglas de penalización.

---

## 5. Sugerencias de Mejora

Para elevar el valor del producto y aumentar el engagement, sugiero implementar:

1. **Sistema de Validación (Aprobación cruzada):** Para grupos con niños/adolescentes, una tarea puede requerir que un Admin (padre/madre) le dé el "Visto Bueno" antes de otorgar los puntos.
2. **Modo Vacaciones/Pausa:** Permite a un usuario "congelar" su asignación y rachas si se va de viaje, recalculando la rotación automáticamente.
3. **Tareas Épicas (Boss Fights):** Tareas muy esporádicas y duras (Ej: "Limpiar el trastero" o "Descongelar la nevera") que dan multiplicadores de puntos y requieren la colaboración de varios miembros.
4. **Opciones de Monetización:**
   - *Freemium:* Gratis hasta 3 miembros y 1 mes de histórico.
   - *Zutsu Pro (Suscripción):* Miembros ilimitados, histórico completo, estadísticas avanzadas, integración con Google Calendar/Alexa, y asignación de tareas impulsada por IA.

---

## 6. Recomendaciones Técnicas

- **Frontend App:** **Flutter**. Es ideal para apps con alta carga visual, gamificación y animaciones (imprescindibles al completar tareas y ganar puntos). Facilita un código único para iOS y Android con rendimiento cuasi-nativo.
- **Backend & DB:** **Firebase / Supabase**.
  - Si priorizas rapidez de desarrollo e integraciones (Notificaciones, Auth): **Firebase** (Firestore, Cloud Functions).
  - Si prefieres queries relacionales robustas (muy útiles para calcular rankings y puntos históricos): **Supabase** (PostgreSQL) + Edge Functions.
- **Gestión de Estado (Flutter):** Riverpod o BLoC.
- **Testing:** 
  - Unitarios para el motor de cálculo de puntos y reglas de rotación (crítico).
  - Tests de integración para los flujos de creación/completado de tareas.
- **Seguridad:** Row Level Security (RLS) en Supabase o Security Rules en Firestore para garantizar que los usuarios solo vean datos de su propio Grupo.

---

## 7. Ejemplo de User Stories

### Must Have (MVP)
1. **Como Admin**, quiero crear un grupo y generar un código de invitación para que mi familia se una.
2. **Como usuario**, quiero ver mis tareas pendientes del día en la pantalla principal para saber qué me toca hacer.
3. **Como usuario**, quiero marcar una tarea como completada para recibir mis puntos inmediatamente.
4. **Como Admin**, quiero configurar la penalización por retraso para fomentar la responsabilidad.
5. **Como usuario**, quiero visualizar el ranking mensual para saber si estoy aportando mi parte al hogar.

### Should Have (Fase 2)
6. **Como usuario**, quiero canjear mis puntos acumulados por una recompensa del Market para disfrutar de mi esfuerzo.
7. **Como Admin**, quiero establecer un límite anual a ciertas recompensas para evitar abusos (ej. "Ir al cine" max 2 veces).
8. **Como usuario**, quiero que la app rote automáticamente la tarea de "Bajar la basura" semanalmente para no tener que asignarla a mano.

### Could Have (Fase 3)
9. **Como usuario**, quiero sincronizar mis tareas con Google Calendar para tenerlas junto a mis reuniones de trabajo.
10. **Como usuario padre/madre**, quiero que las tareas de mi hijo queden en estado "Pendiente de revisión" hasta que yo apruebe la calidad de la limpieza.

---

## 8. Borrador de Copy y Textos

### Eslogan Principal
> *"Zutsu Tasker: El equilibrio empieza en casa."*
> *(Alternativa: "Cada uno su parte, un hogar en armonía.")*

### Descripción Corta (App Stores - Máx 3 frases)
> "Zutsu Tasker transforma las tareas del hogar en un juego justo y colaborativo. Reparte las responsabilidades, completa tus tareas para ganar puntos y canjéalos por recompensas increíbles. Dile adiós a las discusiones y descubre quién es el verdadero héroe de la casa."

### Pantallas de Onboarding

**Pantalla 1: Adiós a las discusiones**
*(Ilustración: Dos personas chocando los cinco frente a una casa limpia)*
> **El fin del "te toca a ti"**
> Organiza y reparte las tareas del hogar de forma transparente. Con Zutsu, siempre sabrás quién hace qué.

**Pantalla 2: Gamifica tu rutina**
*(Ilustración: Trofeo, estrellas y un check verde animado)*
> **Completa y acumula puntos**
> Cada tarea tiene un valor basado en su esfuerzo. Haz tu parte, mantén tu racha y sube en el ranking del grupo.

**Pantalla 3: Recompensas que motivan**
*(Ilustración: Un ticket de cine, un mando de consola y un café)*
> **Tu esfuerzo tiene premio**
> ¿Acumulaste suficientes puntos? Canjéalos en el Market por recompensas que el resto del grupo deberá cumplir por ti. ¡El equilibrio empieza ahora!
