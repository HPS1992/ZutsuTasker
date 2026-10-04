import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker"
files = {}

# 1. Update Schema
schema_path = os.path.join(base_dir, "backend/prisma/schema.prisma")
with open(schema_path, "r") as f:
    schema = f.read()

if "icon_name" not in schema:
    schema = schema.replace(
        "penalty_enabled  Boolean      @default(true)",
        "penalty_enabled  Boolean      @default(true)\n  icon_name        String?      @default(\"checkbox\")\n  image_uri        String?"
    )
    schema = schema.replace(
        "cost_points Int",
        "cost_points Int\n  icon_name   String? @default(\"gift\")\n  image_uri   String?"
    )
    with open(schema_path, "w") as f:
        f.write(schema)

# 2. Update Backend Routes
task_routes = os.path.join(base_dir, "backend/src/routes/taskRoutes.ts")
with open(task_routes, "r") as f:
    tr = f.read()
tr = tr.replace(
    "fixed_user_id, requires_photo }",
    "fixed_user_id, requires_photo, icon_name, image_uri }"
).replace(
    "requires_photo: requires_photo === true",
    "requires_photo: requires_photo === true, icon_name: icon_name || 'checkbox', image_uri: image_uri || null"
)
with open(task_routes, "w") as f:
    f.write(tr)

reward_routes = os.path.join(base_dir, "backend/src/routes/rewardRoutes.ts")
with open(reward_routes, "r") as f:
    rr = f.read()
rr = rr.replace(
    "const { title, cost_points } = req.body;",
    "const { title, cost_points, icon_name, image_uri } = req.body;"
).replace(
    "title, cost_points: parseInt(cost_points)",
    "title, cost_points: parseInt(cost_points), icon_name: icon_name || 'gift', image_uri: image_uri || null"
)
with open(reward_routes, "w") as f:
    f.write(rr)


# 3. TaskCard.tsx
files["mobile/src/components/TaskCard.tsx"] = """import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform, Alert, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTaskStore } from '../store/useTaskStore';
import { LinearGradient } from 'expo-linear-gradient';

export const TaskCard = ({ item, currentUserId, onComplete }: any) => {
  const { claimTask, stealTask, approveTask } = useTaskStore();
  const isMine = item.assigned_to?.id === currentUserId;
  const isPendingReview = item.status === 'PENDING_REVIEW';
  const hasBounty = item.bounty_points && item.bounty_points > item.template.points;
  const displayPoints = item.bounty_points || item.template.points;

  const handleClaim = async () => { try { await claimTask(item.id); } catch(e: any) { alert(e.message); } };
  const handleSteal = async () => {
    const confirmSteal = async () => { try { await stealTask(item.id); } catch(e: any) { alert(e.message); } };
    if (Platform.OS === 'web') { if (window.confirm('¿Robar esta tarea?')) await confirmSteal(); } 
    else { Alert.alert('Robar', '¿Seguro?', [{ text: 'Cancelar', style: 'cancel' }, { text: '¡Robar!', style: 'destructive', onPress: confirmSteal }]); }
  };
  const handleApprove = async () => { try { await approveTask(item.id); } catch(e: any) { alert(e.message); } };

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.titleRow}>
          <View style={[styles.iconBox, item.template.image_uri && {padding: 0, backgroundColor: 'transparent'}]}>
            {item.template.image_uri ? (
               <Image source={{ uri: item.template.image_uri }} style={{width: 44, height: 44, borderRadius: 16}} />
            ) : (
               <Ionicons name={item.template.icon_name || 'checkbox'} size={24} color="#6366F1" />
            )}
          </View>
          <View style={{flex: 1}}>
            <Text style={styles.title}>{item.template.title}</Text>
            {item.template.requires_photo && <Text style={styles.photoRequiredText}>📸 Requiere Foto</Text>}
          </View>
        </View>
        <View style={[styles.pointsBadge, hasBounty && styles.bountyBadge]}>
          <Text style={[styles.pointsText, hasBounty && styles.bountyText]}>{hasBounty ? '🔥' : '⭐'} {displayPoints} pts</Text>
        </View>
      </View>

      <View style={styles.detailsRow}>
        <View style={styles.infoChip}><Ionicons name="calendar-outline" size={14} color="#64748B" /><Text style={styles.infoText}>{new Date(item.due_date).toLocaleDateString()}</Text></View>
        {item.assigned_to ? (
          <View style={styles.infoChip}><Ionicons name="person-circle-outline" size={16} color="#64748B" /><Text style={[styles.infoText, isMine && {color: '#6366F1', fontWeight: 'bold'}]}>{isMine ? 'Tuya' : item.assigned_to.name}</Text></View>
        ) : (
          <View style={[styles.infoChip, { backgroundColor: '#FEF3C7', borderColor: '#FCD34D' }]}><Ionicons name="hand-right-outline" size={14} color="#D97706" /><Text style={[styles.infoText, {color: '#D97706', fontWeight: 'bold'}]}>¡Libre!</Text></View>
        )}
      </View>

      <View style={styles.actions}>
        {item.status === 'PENDING' && !item.assigned_to && (
          <TouchableOpacity onPress={handleClaim} style={{ flex: 1 }}><LinearGradient colors={['#6366F1', '#4F46E5']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>¡Me la pido!</Text></LinearGradient></TouchableOpacity>
        )}
        {item.status === 'PENDING' && item.assigned_to && (
          isMine ? (
            <TouchableOpacity onPress={onComplete} style={{ flex: 1 }}><LinearGradient colors={['#10B981', '#059669']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>Completar</Text></LinearGradient></TouchableOpacity>
          ) : (
            new Date(item.due_date) < new Date() && (
              <TouchableOpacity onPress={handleSteal} style={{ flex: 1 }}><LinearGradient colors={['#F43F5E', '#E11D48']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>🥷 ¡Robar! (+150%)</Text></LinearGradient></TouchableOpacity>
            )
          )
        )}
        {isPendingReview && (
          <View style={{ flex: 1, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
            <View style={[styles.primaryButton, { flex: 1, backgroundColor: '#FEF3C7' }]}><Text style={{ color: '#D97706', fontWeight: 'bold' }}>⏳ Revisando...</Text></View>
            {!isMine && <TouchableOpacity onPress={handleApprove} style={{ flex: 1 }}><LinearGradient colors={['#8B5CF6', '#7C3AED']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>✅ Aprobar</Text></LinearGradient></TouchableOpacity>}
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderRadius: 24, padding: 20, marginBottom: 16, borderWidth: 1, borderColor: 'rgba(226, 232, 240, 0.8)', shadowColor: '#94A3B8', shadowOpacity: 0.1, shadowRadius: 20, shadowOffset: { width: 0, height: 10 }, elevation: 4 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  iconBox: { backgroundColor: '#EEF2FF', padding: 10, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 18, fontWeight: '800', color: '#0F172A', flexWrap: 'wrap', marginRight: 8 },
  photoRequiredText: { fontSize: 12, color: '#DB2777', fontWeight: 'bold', marginTop: 2 },
  pointsBadge: { backgroundColor: '#FEF3C7', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  bountyBadge: { backgroundColor: '#FEE2E2' },
  pointsText: { color: '#B45309', fontWeight: '900', fontSize: 14 },
  bountyText: { color: '#E11D48' },
  detailsRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  infoChip: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#F8FAFC', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: '#F1F5F9' },
  infoText: { color: '#64748B', fontSize: 13, fontWeight: '600' },
  actions: { flexDirection: 'row', gap: 10 },
  primaryButton: { paddingVertical: 14, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  primaryButtonText: { color: '#fff', fontWeight: '800', fontSize: 15, letterSpacing: 0.5 },
});
"""

# 4. TasksScreen.tsx (Add IconPicker and ImagePicker)
tasks_screen = os.path.join(base_dir, "mobile/src/screens/TasksScreen.tsx")
with open(tasks_screen, "r") as f:
    ts = f.read()

ts = ts.replace(
    "const [requiresPhoto, setRequiresPhoto] = useState(false);",
    "const [requiresPhoto, setRequiresPhoto] = useState(false);\n  const [iconName, setIconName] = useState('checkbox');\n  const [imageUri, setImageUri] = useState<string | null>(null);"
)
ts = ts.replace(
    "fixed_user_id: fixedUser, requires_photo: requiresPhoto",
    "fixed_user_id: fixedUser, requires_photo: requiresPhoto, icon_name: iconName, image_uri: imageUri"
)
ts = ts.replace(
    "setPoints(pt.points.toString());",
    "setPoints(pt.points.toString()); setIconName(pt.icon);"
)

icon_list = "const TASK_ICONS = ['checkbox', 'trash', 'bed', 'water', 'shirt', 'paw', 'car', 'cart', 'hammer', 'book', 'barbell', 'restaurant'];"
ts = ts.replace("const FREQUENCIES", icon_list + "\nconst FREQUENCIES")

image_picker_logic = """
  const handlePickIconImage = async () => {
    let result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5, base64: true });
    if (!result.canceled && result.assets[0].base64) {
      setImageUri(`data:image/jpeg;base64,${result.assets[0].base64}`);
    }
  };
"""
ts = ts.replace("const handleCreate = async () => {", image_picker_logic + "\n  const handleCreate = async () => {")

icon_picker_ui = """
              <Text style={styles.label}>Icono de la Tarea:</Text>
              <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 20}}>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  {TASK_ICONS.map(ic => (
                    <TouchableOpacity key={ic} style={[styles.iconSelectBtn, iconName === ic && !imageUri && styles.iconSelectBtnActive]} onPress={() => {setIconName(ic); setImageUri(null);}}>
                      <Ionicons name={ic as any} size={28} color={iconName === ic && !imageUri ? '#6366F1' : '#94A3B8'} />
                    </TouchableOpacity>
                  ))}
                </ScrollView>
                <TouchableOpacity style={styles.imagePickBtn} onPress={handlePickIconImage}>
                  {imageUri ? <Image source={{uri: imageUri}} style={{width: 44, height: 44, borderRadius: 12}} /> : <Ionicons name="image" size={24} color="#64748B" />}
                </TouchableOpacity>
              </View>
"""
ts = ts.replace("<Text style={styles.label}>Frecuencia:</Text>", icon_picker_ui + "\n              <Text style={styles.label}>Frecuencia:</Text>")
ts = ts.replace("import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView, Switch, Platform } from 'react-native';", "import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Modal, TextInput, ScrollView, Switch, Platform, Image } from 'react-native';")

styles_update = """
  iconSelectBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F8FAFC', marginRight: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  iconSelectBtnActive: { backgroundColor: '#EEF2FF', borderColor: '#6366F1' },
  imagePickBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F1F5F9', borderWidth: 1, borderColor: '#E2E8F0', borderStyle: 'dashed', justifyContent: 'center', alignItems: 'center', width: 48, height: 48, marginLeft: 8 },
"""
ts = ts.replace("const styles = StyleSheet.create({", "const styles = StyleSheet.create({\n" + styles_update)

with open(tasks_screen, "w") as f:
    f.write(ts)


# 5. MarketScreen.tsx Update
market_screen = os.path.join(base_dir, "mobile/src/screens/MarketScreen.tsx")
with open(market_screen, "r") as f:
    ms = f.read()

ms = ms.replace(
    "const [cost, setCost] = useState('');",
    "const [cost, setCost] = useState('');\n  const [iconName, setIconName] = useState('gift');\n  const [imageUri, setImageUri] = useState<string | null>(null);"
)
ms = ms.replace(
    "{ title, cost_points: parseInt(cost) }",
    "{ title, cost_points: parseInt(cost), icon_name: iconName, image_uri: imageUri }"
)
ms = ms.replace(
    "import * as ImagePicker from 'expo-image-picker';", ""
)
ms = ms.replace(
    "import { LinearGradient } from 'expo-linear-gradient';",
    "import { LinearGradient } from 'expo-linear-gradient';\nimport * as ImagePicker from 'expo-image-picker';"
)
ms = ms.replace("import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, ActivityIndicator, Modal, TextInput, Platform, ScrollView, Alert } from 'react-native';", "import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, ActivityIndicator, Modal, TextInput, Platform, ScrollView, Alert, Image } from 'react-native';")


reward_icons_list = "const REWARD_ICONS = ['gift', 'pizza', 'beer', 'game-controller', 'airplane', 'ticket', 'film', 'cash', 'cafe', 'headset', 'bag'];"
ms = ms.replace("export default function MarketScreen() {", reward_icons_list + "\n\nexport default function MarketScreen() {")

ms_image_picker = """
  const handlePickIconImage = async () => {
    let result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.5, base64: true });
    if (!result.canceled && result.assets[0].base64) setImageUri(`data:image/jpeg;base64,${result.assets[0].base64}`);
  };
"""
ms = ms.replace("const handleCreate = async () => {", ms_image_picker + "\n  const handleCreate = async () => {")

ms_icon_picker = """
            <Text style={styles.label}>Icono o Imagen:</Text>
            <View style={{flexDirection: 'row', alignItems: 'center', marginBottom: 20}}>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  {REWARD_ICONS.map(ic => (
                    <TouchableOpacity key={ic} style={[styles.iconSelectBtn, iconName === ic && !imageUri && styles.iconSelectBtnActive]} onPress={() => {setIconName(ic); setImageUri(null);}}>
                      <Ionicons name={ic as any} size={28} color={iconName === ic && !imageUri ? '#D97706' : '#94A3B8'} />
                    </TouchableOpacity>
                  ))}
                </ScrollView>
                <TouchableOpacity style={styles.imagePickBtn} onPress={handlePickIconImage}>
                  {imageUri ? <Image source={{uri: imageUri}} style={{width: 44, height: 44, borderRadius: 12}} /> : <Ionicons name="image" size={24} color="#64748B" />}
                </TouchableOpacity>
            </View>
"""
ms = ms.replace("<View style={styles.modalButtonsFixed}>", ms_icon_picker + "\n            <View style={styles.modalButtonsFixed}>")

ms_card_render = """
  const renderReward = ({ item }: any) => (
    <View style={styles.card}>
      <View style={[styles.iconBox, item.image_uri && {padding: 0, backgroundColor: 'transparent'}]}>
        {item.image_uri ? (
           <Image source={{ uri: item.image_uri }} style={{width: 44, height: 44, borderRadius: 16}} />
        ) : (
           <Ionicons name={item.icon_name || 'gift'} size={24} color="#D97706" />
        )}
      </View>
      <View style={{flex: 1}}>
         <Text style={styles.title}>{item.title}</Text>
         <View style={styles.pointsPill}>
            <Text style={styles.points}>⭐ {item.cost_points} pts</Text>
         </View>
      </View>
      <View style={{flexDirection: 'row', gap: 10, alignItems: 'center'}}>
        <TouchableOpacity onPress={() => handleRedeem(item.id)}>
          <LinearGradient colors={['#10B981', '#059669']} style={styles.redeemButton}>
            <Text style={styles.redeemText}>Comprar</Text>
          </LinearGradient>
        </TouchableOpacity>
        {isAdmin && (
          <TouchableOpacity onPress={() => handleDelete(item.id)} style={styles.deleteBtn}>
            <Ionicons name="trash" size={20} color="#EF4444" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
"""

ms_old_render = """
  const renderReward = ({ item }: any) => (
    <View style={styles.card}>
      <View style={{flex: 1}}>
         <Text style={styles.title}>{item.title}</Text>
         <View style={styles.pointsPill}>
            <Text style={styles.points}>⭐ {item.cost_points} pts</Text>
         </View>
      </View>
      <View style={{flexDirection: 'row', gap: 10, alignItems: 'center'}}>
        <TouchableOpacity onPress={() => handleRedeem(item.id)}>
          <LinearGradient colors={['#10B981', '#059669']} style={styles.redeemButton}>
            <Text style={styles.redeemText}>Comprar</Text>
          </LinearGradient>
        </TouchableOpacity>
        {isAdmin && (
          <TouchableOpacity onPress={() => handleDelete(item.id)} style={styles.deleteBtn}>
            <Ionicons name="trash" size={20} color="#EF4444" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
"""
ms = ms.replace(ms_old_render.strip(), ms_card_render.strip())

ms_styles_update = """
  iconBox: { backgroundColor: '#FEF3C7', padding: 12, borderRadius: 16, justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  iconSelectBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F8FAFC', marginRight: 10, borderWidth: 1, borderColor: '#F1F5F9' },
  iconSelectBtnActive: { backgroundColor: '#FEF3C7', borderColor: '#F59E0B' },
  imagePickBtn: { padding: 10, borderRadius: 16, backgroundColor: '#F1F5F9', borderWidth: 1, borderColor: '#E2E8F0', borderStyle: 'dashed', justifyContent: 'center', alignItems: 'center', width: 48, height: 48, marginLeft: 8 },
"""
ms = ms.replace("const styles = StyleSheet.create({", "const styles = StyleSheet.create({\n" + ms_styles_update)

with open(market_screen, "w") as f:
    f.write(ms)

for filepath, content in files.items():
    with open(os.path.join(base_dir, filepath), "w", encoding="utf-8") as f:
        f.write(content)

print("Icons and Images feature implemented.")
