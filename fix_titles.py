import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile/src/screens"

# 1. Update TasksScreen
ts_path = os.path.join(base_dir, "TasksScreen.tsx")
with open(ts_path, "r") as f:
    ts = f.read()

ts = ts.replace("Tu Hogar", "Tareas")
with open(ts_path, "w") as f:
    f.write(ts)

# 2. Update MarketScreen
ms_path = os.path.join(base_dir, "MarketScreen.tsx")
with open(ms_path, "r") as f:
    ms = f.read()

ms = ms.replace("Bazar", "Marketplace")
with open(ms_path, "w") as f:
    f.write(ms)

# 3. Update StatsScreen
ss_path = os.path.join(base_dir, "StatsScreen.tsx")
with open(ss_path, "r") as f:
    ss = f.read()

ss = ss.replace("Equilibrio", "Equidad")
with open(ss_path, "w") as f:
    f.write(ss)
