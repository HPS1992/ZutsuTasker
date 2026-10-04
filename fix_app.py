import os

app_path = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile/App.tsx"
with open(app_path, "r") as f:
    app = f.read()

app = app.replace("import RegisterScreen from './src/screens/RegisterScreen';\n", "")
app = app.replace("<Stack.Screen name=\"Register\" component={RegisterScreen} />", "")
app = app.replace("StyleSheet.absoluteFillObject", "StyleSheet.absoluteFill")

with open(app_path, "w") as f:
    f.write(app)
