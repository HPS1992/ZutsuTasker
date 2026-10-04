import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile"
files = {}

ms_path = os.path.join(base_dir, "src/screens/MarketScreen.tsx")
with open(ms_path, "r") as f:
    ms = f.read()
ms = ms.replace("colors={['#F59E0B', '#D97706']}", "colors={['#4F46E5', '#7C3AED']}")
ms = ms.replace("shadowColor: '#D97706'", "shadowColor: '#4F46E5'")
with open(ms_path, "w") as f:
    f.write(ms)

ss_path = os.path.join(base_dir, "src/screens/StatsScreen.tsx")
with open(ss_path, "r") as f:
    ss = f.read()
ss = ss.replace("colors={['#0F172A', '#1E293B']}", "colors={['#4F46E5', '#7C3AED']}")
ss = ss.replace("shadowColor: '#0F172A'", "shadowColor: '#4F46E5'")
with open(ss_path, "w") as f:
    f.write(ss)
