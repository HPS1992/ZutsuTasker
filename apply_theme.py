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

# Option Chosen: Electric Indigo (#5B3DF5) + Soft Lilac (#E8DEFF)
replacements = {
    "['#4F46E5', '#7C3AED']": "['#5B3DF5', '#957CFF']", # Header gradients
    "['#6366F1', '#4F46E5']": "['#7055F6', '#5B3DF5']", # Primary buttons
    "['#8B5CF6', '#7C3AED']": "['#A28CFF', '#5B3DF5']", # Approve buttons
    "'#6366F1'": "'#5B3DF5'",
    "'#4F46E5'": "'#5B3DF5'",
    "'#7C3AED'": "'#5B3DF5'",
    "'#EEF2FF'": "'#E8DEFF'", # Soft Lilac for backgrounds
    "'#E0E7FF'": "'#D3C1FF'", # Darker Lilac for borders
    "'#F3E8FF'": "'#E8DEFF'", 
    "'#7E22CE'": "'#5B3DF5'"
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
        
print("Color theme updated to Electric Indigo and Soft Lilac.")
