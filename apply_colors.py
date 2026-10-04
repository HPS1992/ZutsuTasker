import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile"
files_to_modify = [
    "App.tsx",
    "src/screens/TasksScreen.tsx",
    "src/screens/MarketScreen.tsx",
    "src/screens/ProfileScreen.tsx",
    "src/screens/StatsScreen.tsx",
    "src/screens/CalendarScreen.tsx",
    "src/components/TaskCard.tsx"
]

replacements = {
    "['#4F46E5', '#7C3AED']": "['#1DB69F', '#C8F3D7']",
    "['#6366F1', '#4F46E5']": "['#25D6BB', '#1DB69F']",
    "['#8B5CF6', '#7C3AED']": "['#3DE2C8', '#1DB69F']",
    "'#6366F1'": "'#1DB69F'",
    "'#4F46E5'": "'#1DB69F'",
    "'#7C3AED'": "'#1DB69F'",
    "'#EEF2FF'": "'#E6FDF4'",
    "'#E0E7FF'": "'#C8F3D7'",
    "'#F3E8FF'": "'#E6FDF4'", 
    "'#7E22CE'": "'#159B87'"
}

for relative_path in files_to_modify:
    filepath = os.path.join(base_dir, relative_path)
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as f:
        content = f.read()
        
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open(filepath, "w") as f:
        f.write(content)
        
print("Color theme updated to Neon Lime and Teal Ink.")
