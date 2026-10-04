import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r") as f:
    schema = f.read()

if "room_name" not in schema:
    schema = schema.replace(
        "image_uri        String?",
        "image_uri        String?\n  room_name        String       @default(\"General\")\n  room_icon        String       @default(\"home\")"
    )
    with open(schema_path, "w") as f:
        f.write(schema)


# 2. Update TaskRoutes (Add GET /rooms/health & update POST /)
task_routes_path = os.path.join(base_dir, "backend/src/routes/taskRoutes.ts")
with open(task_routes_path, "r") as f:
    tr = f.read()

if "/rooms/health" not in tr:
    health_endpoint = """
router.get('/rooms/health', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(404).json({ error: 'No group' });

    const templates = await prisma.taskTemplate.findMany({
      where: { group_id: member.group_id },
      include: { instances: { orderBy: { due_date: 'desc' }, take: 1 } }
    });

    const roomMap = new Map();

    for (const t of templates) {
      const roomName = t.room_name || 'General';
      const roomIcon = t.room_icon || 'home';
      if (!roomMap.has(roomName)) roomMap.set(roomName, { name: roomName, icon: roomIcon, totalHealth: 0, count: 0 });
      
      let tHealth = 100;
      if (t.instances.length > 0) {
        const inst = t.instances[0];
        if (inst.status === 'PENDING') {
          const now = new Date(); now.setHours(0,0,0,0);
          const due = new Date(inst.due_date); due.setHours(0,0,0,0);
          const diffDays = Math.round((due.getTime() - now.getTime()) / 86400000);
          
          if (diffDays >= 2) tHealth = 100;
          else if (diffDays === 1) tHealth = 80;
          else if (diffDays === 0) tHealth = 50;
          else if (diffDays === -1) tHealth = 25;
          else tHealth = 0;
        } else if (inst.status === 'PENDING_REVIEW') {
          tHealth = 90;
        } else if (inst.status === 'COMPLETED') {
          tHealth = 100;
        }
      }
      
      const rm = roomMap.get(roomName);
      rm.totalHealth += tHealth;
      rm.count += 1;
    }

    const rooms = Array.from(roomMap.values()).map((r: any) => ({
      name: r.name,
      icon: r.icon,
      health: Math.round(r.totalHealth / r.count)
    }));

    res.json(rooms);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

router.get('/', requireAuth, async (req, res) => {
"""
    tr = tr.replace("router.get('/', requireAuth, async (req, res) => {", health_endpoint)

    tr = tr.replace(
        "icon_name, image_uri } = req.body;",
        "icon_name, image_uri, room_name, room_icon } = req.body;"
    ).replace(
        "image_uri: image_uri || null",
        "image_uri: image_uri || null, room_name: room_name || 'General', room_icon: room_icon || 'home'"
    )
    with open(task_routes_path, "w") as f:
        f.write(tr)


# 3. Update TasksScreen.tsx (Frontend)
tasks_screen_path = os.path.join(base_dir, "mobile/src/screens/TasksScreen.tsx")
with open(tasks_screen_path, "r") as f:
    ts = f.read()

# Add state and UI for rooms
ts = ts.replace(
    "const [history, setHistory] = useState<any[]>([]);",
    "const [history, setHistory] = useState<any[]>([]);\n  const [rooms, setRooms] = useState<any[]>([]);\n  const [selectedRoomFilter, setSelectedRoomFilter] = useState<string | null>(null);\n  const [roomName, setRoomName] = useState('General');\n  const [roomIcon, setRoomIcon] = useState('home');"
)

ts = ts.replace(
    "fetchTasks();",
    "fetchTasks(); fetchRooms();"
)

fetch_rooms_code = """
  const fetchRooms = async () => {
    try {
      const res = await api.get('/tasks/rooms/health');
      setRooms(res.data);
    } catch (e) {}
  };
"""
ts = ts.replace("const loadHistory = async () => {", fetch_rooms_code + "\n  const loadHistory = async () => {")

ts = ts.replace(
    "image_uri: imageUri",
    "image_uri: imageUri, room_name: roomName, room_icon: roomIcon"
)
ts = ts.replace("fetchTasks();", "fetchTasks(); fetchRooms();")

room_list_ui = """
      {/* ROOMS HEALTH BAR */}
      <View style={{ marginTop: -20, marginBottom: 10 }}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 20, gap: 12 }}>
          <TouchableOpacity onPress={() => setSelectedRoomFilter(null)} style={[styles.roomCard, !selectedRoomFilter && styles.roomCardActive]}>
             <Ionicons name="apps" size={24} color={!selectedRoomFilter ? '#fff' : '#64748B'} />
             <Text style={[styles.roomName, !selectedRoomFilter && {color: '#fff'}]}>Todas</Text>
          </TouchableOpacity>
          {rooms.map(r => {
             const isCritical = r.health <= 25;
             const isWarning = r.health > 25 && r.health <= 60;
             const color = isCritical ? '#EF4444' : (isWarning ? '#F59E0B' : '#10B981');
             const isActive = selectedRoomFilter === r.name;
             return (
               <TouchableOpacity key={r.name} onPress={() => setSelectedRoomFilter(isActive ? null : r.name)} style={[styles.roomCard, isActive && {backgroundColor: color, borderColor: color}]}>
                 <Ionicons name={r.icon as any} size={24} color={isActive ? '#fff' : color} />
                 <Text style={[styles.roomName, isActive && {color: '#fff'}]}>{r.name}</Text>
                 <View style={styles.healthBarBg}>
                   <View style={[styles.healthBarFill, { width: `${r.health}%`, backgroundColor: isActive ? '#fff' : color }]} />
                 </View>
                 {isCritical && !isActive && <Text style={{position: 'absolute', top: -5, right: -5, fontSize: 16}}>🦠</Text>}
               </TouchableOpacity>
             )
          })}
        </ScrollView>
      </View>
"""
ts = ts.replace("<FlatList", room_list_ui + "\n      <FlatList")

# Update FlatList data to filter by selected room
ts = ts.replace(
    "data={tasks}",
    "data={selectedRoomFilter ? tasks.filter(t => t.template.room_name === selectedRoomFilter) : tasks}"
)

# Modal changes for selecting room
predefined_rooms = "const PREDEFINED_ROOMS = [{name: 'General', icon: 'home'}, {name: 'Cocina', icon: 'restaurant'}, {name: 'Baño', icon: 'water'}, {name: 'Salón', icon: 'tv'}, {name: 'Dormitorio', icon: 'bed'}, {name: 'Exterior', icon: 'leaf'}];"
ts = ts.replace("const FREQUENCIES", predefined_rooms + "\nconst FREQUENCIES")

room_modal_ui = """
              <Text style={styles.label}>Habitación / Zona:</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{marginBottom: 20}}>
                {PREDEFINED_ROOMS.map(r => (
                  <TouchableOpacity key={r.name} style={[styles.freqBtn, roomName === r.name && styles.freqBtnActive]} onPress={() => {setRoomName(r.name); setRoomIcon(r.icon);}}>
                    <Ionicons name={r.icon as any} size={16} color={roomName === r.name ? '#6366F1' : '#64748B'} style={{marginRight: 6}} />
                    <Text style={[styles.freqText, roomName === r.name && styles.freqTextActive]}>{r.name}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
"""
ts = ts.replace("<Text style={styles.label}>Icono de la Tarea:</Text>", room_modal_ui + "\n              <Text style={styles.label}>Icono de la Tarea:</Text>")

styles_update = """
  roomCard: { backgroundColor: '#fff', padding: 12, borderRadius: 20, borderWidth: 1, borderColor: '#F1F5F9', alignItems: 'center', minWidth: 80, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10 },
  roomCardActive: { backgroundColor: '#6366F1', borderColor: '#6366F1' },
  roomName: { fontSize: 12, fontWeight: '800', color: '#64748B', marginTop: 4, marginBottom: 8 },
  healthBarBg: { width: '100%', height: 6, backgroundColor: '#F1F5F9', borderRadius: 10, overflow: 'hidden' },
  healthBarFill: { height: '100%', borderRadius: 10 },
"""
ts = ts.replace("const styles = StyleSheet.create({", "const styles = StyleSheet.create({\n" + styles_update)

with open(tasks_screen_path, "w") as f:
    f.write(ts)


# 4. Update TaskCard.tsx
tc_path = os.path.join(base_dir, "mobile/src/components/TaskCard.tsx")
with open(tc_path, "r") as f:
    tc = f.read()

room_badge = """
        <View style={styles.detailsRow}>
          <View style={[styles.infoChip, {backgroundColor: '#EEF2FF', borderColor: '#E0E7FF'}]}>
             <Ionicons name={item.template.room_icon || 'home'} size={14} color="#4F46E5" />
             <Text style={[styles.infoText, {color: '#4F46E5'}]}>{item.template.room_name || 'General'}</Text>
          </View>
"""
tc = tc.replace("<View style={styles.detailsRow}>", room_badge)
with open(tc_path, "w") as f:
    f.write(tc)


print("Room Health and Degradation feature created.")
