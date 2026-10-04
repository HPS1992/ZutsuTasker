import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r") as f:
    schema = f.read()

if "is_stolen" not in schema:
    schema = schema.replace(
        "photo_uri        String?",
        "photo_uri        String?\n  is_stolen        Boolean      @default(false)\n  penalty_applied  Boolean      @default(false)"
    )
    with open(schema_path, "w") as f:
        f.write(schema)

# 2. Update Task Service
task_service_path = os.path.join(base_dir, "backend/src/services/taskService.ts")
with open(task_service_path, "r") as f:
    ts = f.read()

ts = ts.replace(
    "data: { status: 'COMPLETED', completed_at: now, assigned_to: userId }",
    "data: { status: 'COMPLETED', completed_at: now, assigned_to: userId, points_awarded: points, penalty_applied: penaltyApplied }"
)
ts = ts.replace(
    "data: { status: 'COMPLETED', completed_at: now }",
    "data: { status: 'COMPLETED', completed_at: now, points_awarded: points }"
)
ts = ts.replace(
    "data: { status: 'COMPLETED', completed_at: now, assigned_to: thiefId }",
    "data: { status: 'COMPLETED', completed_at: now, assigned_to: thiefId, is_stolen: true, penalty_applied: true, points_awarded: stolenReward }"
)

with open(task_service_path, "w") as f:
    f.write(ts)

# 3. Add History Routes to TaskRoutes and RewardRoutes
task_routes_path = os.path.join(base_dir, "backend/src/routes/taskRoutes.ts")
with open(task_routes_path, "r") as f:
    tr = f.read()

if "/history" not in tr:
    history_route = """
router.get('/history', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.status(400).json({ error: 'No group' });
    const history = await prisma.taskInstance.findMany({
      where: { group_id: member.group_id, status: 'COMPLETED' },
      include: { template: true, assigned_user: true },
      orderBy: { completed_at: 'desc' },
      take: 50 // Limit to last 50 for performance
    });
    res.json(history.map(t => ({...t, assigned_to: t.assigned_user})));
  } catch (e: any) { res.status(500).json({ error: e.message }); }
});
"""
    tr = tr.replace("router.post('/', requireAuth, async (req, res) => {", history_route + "\nrouter.post('/', requireAuth, async (req, res) => {")
    with open(task_routes_path, "w") as f:
        f.write(tr)

reward_routes_path = os.path.join(base_dir, "backend/src/routes/rewardRoutes.ts")
with open(reward_routes_path, "r") as f:
    rr = f.read()

if "/history" not in rr:
    market_history_route = """
router.get('/history', requireAuth, async (req, res) => {
  try {
    const member = await prisma.groupMember.findFirst({ where: { user_id: req.user.id } });
    if (!member) return res.json([]);
    const history = await prisma.rewardRedemption.findMany({
      where: { reward: { group_id: member.group_id }, status: 'COMPLETED' },
      include: { reward: true, user: true },
      orderBy: { redeemed_at: 'desc' },
      take: 50
    });
    res.json(history);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});
"""
    rr = rr.replace("router.get('/redemptions', requireAuth, async (req, res) => {", market_history_route + "\nrouter.get('/redemptions', requireAuth, async (req, res) => {")
    with open(reward_routes_path, "w") as f:
        f.write(rr)


# 4. Update API
api_path = os.path.join(base_dir, "mobile/src/services/api.ts")
with open(api_path, "r") as f:
    api = f.read()

if "getTasksHistory" not in api:
    api += "\nexport const getTasksHistory = async () => (await api.get('/tasks/history')).data;\n"
    api += "export const getRewardsHistory = async () => (await api.get('/rewards/history')).data;\n"
    with open(api_path, "w") as f:
        f.write(api)

# 5. TasksScreen.tsx UI Update
tasks_screen = os.path.join(base_dir, "mobile/src/screens/TasksScreen.tsx")
with open(tasks_screen, "r") as f:
    ts_ui = f.read()

ts_ui = ts_ui.replace(
    "const { tasks, fetchTasks, completeTask } = useTaskStore();",
    "const { tasks, fetchTasks, completeTask } = useTaskStore();\n  const [historyModal, setHistoryModal] = useState(false);\n  const [history, setHistory] = useState<any[]>([]);"
)
ts_ui = ts_ui.replace(
    "import { api, getMembers } from '../services/api';",
    "import { api, getMembers, getTasksHistory } from '../services/api';"
)

open_history_func = """
  const loadHistory = async () => {
    try {
      const data = await getTasksHistory();
      setHistory(data);
      setHistoryModal(true);
    } catch(e) {}
  };
"""
ts_ui = ts_ui.replace("const handleComplete = async (item: any) => {", open_history_func + "\n  const handleComplete = async (item: any) => {")

header_replacement = """
      <View style={[styles.header, {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}]}>
        <Text style={styles.headerTitle}>Planificación</Text>
        <TouchableOpacity onPress={loadHistory} style={{padding: 8, backgroundColor: '#EEF2FF', borderRadius: 12}}>
           <Ionicons name="time-outline" size={24} color="#4F46E5" />
        </TouchableOpacity>
      </View>
"""
ts_ui = ts_ui.replace("""      <View style={styles.header}>
        <Text style={styles.headerTitle}>Planificación</Text>
      </View>""", header_replacement)

history_modal_jsx = """
      <Modal visible={historyModal} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, {height: '90%'}]}>
            <View style={{flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16}}>
              <Text style={styles.modalTitle}>Historial de Tareas</Text>
              <TouchableOpacity onPress={() => setHistoryModal(false)}><Ionicons name="close" size={28} color="#6B7280" /></TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false}>
              {history.length === 0 ? <Text style={{color: '#6B7280', textAlign: 'center', marginTop: 20}}>No hay tareas completadas aún.</Text> : null}
              {history.map(item => (
                <View key={item.id} style={{backgroundColor: '#F9FAFB', padding: 16, borderRadius: 12, marginBottom: 12, borderWidth: 1, borderColor: '#F3F4F6'}}>
                  <View style={{flexDirection: 'row', justifyContent: 'space-between'}}>
                     <Text style={{fontSize: 16, fontWeight: 'bold', color: '#111827'}}>{item.template?.title || 'Tarea borrada'}</Text>
                     <Text style={{color: '#F59E0B', fontWeight: 'bold'}}>+{item.points_awarded || item.template?.points} pts</Text>
                  </View>
                  <Text style={{color: '#4B5563', marginTop: 4}}>👤 Realizada por: {item.assigned_to?.name || 'Desconocido'}</Text>
                  <Text style={{color: '#9CA3AF', fontSize: 12, marginTop: 4}}>📅 {new Date(item.completed_at).toLocaleString('es-ES')}</Text>
                  
                  <View style={{flexDirection: 'row', gap: 8, marginTop: 8}}>
                    {item.is_stolen && <Text style={{backgroundColor: '#EDE9FE', color: '#8B5CF6', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8, fontSize: 12, fontWeight: 'bold'}}>🥷 Tarea Robada</Text>}
                    {item.penalty_applied && <Text style={{backgroundColor: '#FEE2E2', color: '#EF4444', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8, fontSize: 12, fontWeight: 'bold'}}>⚠️ Penalizó al responsable</Text>}
                  </View>
                </View>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
"""
ts_ui = ts_ui.replace("</SafeAreaView>", history_modal_jsx + "\n    </SafeAreaView>")

with open(tasks_screen, "w") as f:
    f.write(ts_ui)

# 6. MarketScreen.tsx UI Update
market_screen = os.path.join(base_dir, "mobile/src/screens/MarketScreen.tsx")
with open(market_screen, "r") as f:
    ms_ui = f.read()

ms_ui = ms_ui.replace(
    "import { getRewards, createReward, deleteReward, redeemReward, getRedemptions, completeRedemption, api } from '../services/api';",
    "import { getRewards, createReward, deleteReward, redeemReward, getRedemptions, completeRedemption, getRewardsHistory, api } from '../services/api';"
)
ms_ui = ms_ui.replace(
    "const [modalVisible, setModalVisible] = useState(false);",
    "const [modalVisible, setModalVisible] = useState(false);\n  const [historyModal, setHistoryModal] = useState(false);\n  const [history, setHistory] = useState<any[]>([]);"
)

ms_open_history = """
  const loadHistory = async () => {
    try {
      const data = await getRewardsHistory();
      setHistory(data);
      setHistoryModal(true);
    } catch(e) {}
  };
"""
ms_ui = ms_ui.replace("const handleCreate = async () => {", ms_open_history + "\n  const handleCreate = async () => {")

ms_header_repl = """
      <View style={[styles.header, {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}]}>
        <View>
          <Text style={styles.headerTitle}>Marketplace</Text>
          <Text style={styles.subtitle}>Gasta tus puntos ganados</Text>
        </View>
        <TouchableOpacity onPress={loadHistory} style={{padding: 8, backgroundColor: '#EEF2FF', borderRadius: 12}}>
           <Ionicons name="time-outline" size={24} color="#4F46E5" />
        </TouchableOpacity>
      </View>
"""
ms_ui = ms_ui.replace("""      <View style={styles.header}>
        <Text style={styles.headerTitle}>Marketplace</Text>
        <Text style={styles.subtitle}>Gasta tus puntos ganados</Text>
      </View>""", ms_header_repl)

ms_history_modal = """
      <Modal visible={historyModal} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, {height: '90%'}]}>
            <View style={{flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16}}>
              <Text style={styles.modalTitle}>Historial de Canjes</Text>
              <TouchableOpacity onPress={() => setHistoryModal(false)}><Ionicons name="close" size={28} color="#6B7280" /></TouchableOpacity>
            </View>
            <ScrollView showsVerticalScrollIndicator={false}>
              {history.length === 0 ? <Text style={{color: '#6B7280', textAlign: 'center', marginTop: 20}}>No hay canjes completados aún.</Text> : null}
              {history.map(item => (
                <View key={item.id} style={{backgroundColor: '#F9FAFB', padding: 16, borderRadius: 12, marginBottom: 12, borderWidth: 1, borderColor: '#F3F4F6'}}>
                  <View style={{flexDirection: 'row', justifyContent: 'space-between'}}>
                     <Text style={{fontSize: 16, fontWeight: 'bold', color: '#111827'}}>{item.reward?.title || 'Premio borrado'}</Text>
                  </View>
                  <Text style={{color: '#4B5563', marginTop: 4}}>👤 Disfrutado por: {item.user?.name || 'Desconocido'}</Text>
                  <Text style={{color: '#9CA3AF', fontSize: 12, marginTop: 4}}>📅 Canjeado: {new Date(item.redeemed_at).toLocaleString('es-ES')}</Text>
                  <Text style={{backgroundColor: '#D1FAE5', color: '#065F46', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8, fontSize: 12, fontWeight: 'bold', alignSelf: 'flex-start', marginTop: 8}}>✅ Completado</Text>
                </View>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
"""
ms_ui = ms_ui.replace("</SafeAreaView>", ms_history_modal + "\n    </SafeAreaView>")

with open(market_screen, "w") as f:
    f.write(ms_ui)

print("History system fully implemented.")
