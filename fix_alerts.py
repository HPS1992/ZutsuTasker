import os

base_dir = "/Volumes/IA_SSD/proyectos/ZutsuTasker/mobile/src/screens"

# 1. Fix MarketScreen.tsx
market_path = os.path.join(base_dir, "MarketScreen.tsx")
with open(market_path, "r") as f:
    market = f.read()

market = market.replace(
    "import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Alert, ActivityIndicator, Modal, TextInput } from 'react-native';",
    "import { View, Text, StyleSheet, SafeAreaView, FlatList, TouchableOpacity, Alert, ActivityIndicator, Modal, TextInput, Platform } from 'react-native';"
)

old_market_delete = """const handleDelete = (id: string) => {
    Alert.alert('Borrar recompensa', '¿Estás seguro?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Borrar', style: 'destructive', onPress: async () => {
        try {
          await deleteReward(id);
          fetchData();
        } catch(e: any) { Alert.alert('Error', e.response?.data?.error || 'No se pudo borrar'); }
      }}
    ]);
  };"""

new_market_delete = """const handleDelete = async (id: string) => {
    const confirmDelete = async () => {
      try {
        await deleteReward(id);
        fetchData();
      } catch(e: any) { alert(e.response?.data?.error || 'No se pudo borrar'); }
    };

    if (Platform.OS === 'web') {
      if (window.confirm('¿Estás seguro de borrar esta recompensa?')) {
        await confirmDelete();
      }
    } else {
      Alert.alert('Borrar recompensa', '¿Estás seguro?', [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Borrar', style: 'destructive', onPress: confirmDelete }
      ]);
    }
  };"""

if old_market_delete in market:
    market = market.replace(old_market_delete, new_market_delete)
    with open(market_path, "w") as f:
        f.write(market)


# 2. Fix ProfileScreen.tsx
profile_path = os.path.join(base_dir, "ProfileScreen.tsx")
with open(profile_path, "r") as f:
    profile = f.read()

profile = profile.replace(
    "import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, Alert, TextInput, ScrollView, Share } from 'react-native';",
    "import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, Alert, TextInput, ScrollView, Share, Platform } from 'react-native';"
)

old_profile_kick = """const handleKick = (userId: string, name: string) => {
    Alert.alert('Expulsar', `¿Seguro que quieres expulsar a ${name}?`, [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Expulsar', style: 'destructive', onPress: async () => {
          try { await kickMember(userId); fetchData(); } 
          catch(e) { Alert.alert('Error', 'No se pudo expulsar'); }
      }}
    ]);
  };"""

new_profile_kick = """const handleKick = (userId: string, name: string) => {
    const confirmKick = async () => {
      try { await kickMember(userId); fetchData(); } 
      catch(e) { alert('No se pudo expulsar'); }
    };

    if (Platform.OS === 'web') {
      if (window.confirm(`¿Seguro que quieres expulsar a ${name}?`)) {
        confirmKick();
      }
    } else {
      Alert.alert('Expulsar', `¿Seguro que quieres expulsar a ${name}?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Expulsar', style: 'destructive', onPress: confirmKick }
      ]);
    }
  };"""

if old_profile_kick in profile:
    profile = profile.replace(old_profile_kick, new_profile_kick)
    with open(profile_path, "w") as f:
        f.write(profile)

print("Web Alert compatibility fixes applied.")
