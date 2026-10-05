# APK Android

Se necesitan Node.js, JDK 17 y el SDK Android. Configura `JAVA_HOME` y `ANDROID_HOME` para tu equipo (o `android/local.properties` con `sdk.dir`).

Desde `mobile`:

```sh
npm ci
npm run apk
```

El APK autónomo se genera en `android/app/build/outputs/apk/release/app-release.apk`. No necesita Metro ni Expo Go y utiliza la firma de pruebas existente en Gradle.

Para comprobar las dependencias de Expo:

```sh
npx expo install --check
```

`app.json` y `android/gradle.properties` deben usar Hermes. El host nativo de Expo SDK 57 crea una instancia Hermes; desactivar `hermesEnabled` elimina sus bibliotecas del APK y provoca `SoLoaderDSONotFoundError: libhermestooling.so` al abrirlo. Mantén también `newArchEnabled=true` para React Native 0.86.

El sonido utiliza `expo-audio` de SDK 57. `expo-av` 16 no es compatible con la ABI de React Native 0.86 y provocaba un segundo cierre nativo al cargar `libexpo-av.so`.

La dirección de API predeterminada es `https://zutsu-tasker.vercel.app/api`. Puedes definir `EXPO_PUBLIC_API_URL` en `mobile/.env` antes de compilar para utilizar otro backend; la URL se incluye en el bundle del APK.

Para instalar y revisar el arranque con un dispositivo conectado:

```sh
adb install -r android/app/build/outputs/apk/release/app-release.apk
adb logcat -c
adb shell am start -W -n com.zutsu.tasker/.MainActivity
adb logcat -d -s AndroidRuntime ReactNativeJS
```

El backend también debe estar desplegado y conectado a PostgreSQL para iniciar sesión y gestionar tareas. Se han añadido `icon_name` e `image_uri` al modelo `Reward` porque la API ya los utilizaba. Para actualizar un backend existente, desde `backend`, con `DATABASE_URL` configurada:

```sh
npx prisma generate
npx prisma db push
npm run build
npm start
```

Estos comandos actualizan el backend; compilar el APK no modifica una base de datos ni despliega el servidor.

## Comprobaciones realizadas

El APK release se ha instalado en un emulador Android 14 ARM64. Se ha comprobado el arranque en frío, la recuperación de una sesión dañada, la restauración del formato de sesión anterior, el cierre de sesión y la navegación por Inicio, Tareas, Calendario, Premios, Equidad y Perfil. La navegación se probó con una sesión simulada y un token rechazado por el servidor; los flujos autenticados se probaron con el backend local aislado.

El backend compila y su esquema Prisma valida. La prueba de integración arranca PostgreSQL y el servidor de producción con datos temporales y comprueba registro, login, grupos, tareas, recompensas, estadísticas y vacaciones. Se puede repetir desde `backend` con:

```sh
npm run smoke
```

Requiere las herramientas de PostgreSQL (`initdb` y `pg_ctl`) en `PATH`, o su directorio en `PG_BIN`. La prueba utiliza una base de datos temporal propia y no utiliza `DATABASE_URL` del proyecto.
