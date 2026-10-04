import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, ActivityIndicator, TouchableOpacity, TextInput, Alert } from 'react-native';
import { api, createGroup, joinGroup } from '../services/api';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { registerForPushNotificationsAsync } from '../services/notifications';

export default function HomeScreen() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const navigation = useNavigation<any>();

  // States for No Group
  const [newGroupName, setNewGroupName] = useState('');
  const [inviteCode, setInviteCode] = useState('');

  const fetchDashboard = () => {
    api.get('/users/dashboard')
      .then(res => setData(res.data))
      .catch(err => setError(err.message));
  };

  useFocusEffect(
    useCallback(() => {
      fetchDashboard();
    }, [])
  );

  useEffect(() => {
    registerForPushNotificationsAsync();
  }, []);

  const handleCreateGroup = async () => {
    if(!newGroupName) return Alert.alert('Error', 'Pon un nombre');
    try { await createGroup(newGroupName); fetchDashboard(); } 
    catch(e) { Alert.alert('Error', 'No se pudo crear'); }
  };

  const handleJoinGroup = async () => {
    if(!inviteCode) return Alert.alert('Error', 'Pon el código');
    try { await joinGroup(inviteCode); fetchDashboard(); } 
    catch(e) { Alert.alert('Error', 'Código inválido'); }
  };

  if (error) return <SafeAreaView style={styles.container}><Text style={{padding:20, color:'red'}}>Error cargando: {error}</Text></SafeAreaView>;
  if (!data) return <SafeAreaView style={styles.container}><ActivityIndicator style={{marginTop: 50}} color="#4F46E5" /></SafeAreaView>;

  // Si el usuario acaba de registrarse y no tiene grupo
  if (!data.groupId) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.noGroupContainer}>
          <Text style={styles.greeting}>Bienvenido, {data.name} 👋</Text>
          <Text style={styles.noGroupDesc}>Para empezar a usar Zutsu, necesitas crear un grupo para tu hogar o unirte a uno existente.</Text>
          
          <View style={styles.actionCard}>
            <Text style={styles.sectionTitle}>Crear un nuevo hogar</Text>
            <TextInput style={styles.input} placeholder="Ej. Piso Estudiantes" value={newGroupName} onChangeText={setNewGroupName} />
            <TouchableOpacity style={styles.primaryButton} onPress={handleCreateGroup}>
               <Text style={styles.buttonText}>Crear y ser Administrador</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.actionCard}>
            <Text style={styles.sectionTitle}>Unirse a un hogar</Text>
            <TextInput style={styles.input} placeholder="Código de invitación (ID)" value={inviteCode} onChangeText={setInviteCode} />
            <TouchableOpacity style={styles.secondaryButton} onPress={handleJoinGroup}>
               <Text style={[styles.buttonText, {color: '#4F46E5'}]}>Unirse al grupo</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
            <Text style={styles.greeting}>¡Hola, {data.name}! 🚀</Text>
            <TouchableOpacity onPress={() => navigation.navigate('Ajustes')}><Ionicons name="settings-outline" size={28} color="#4F46E5"/></TouchableOpacity>
          </View>
          <Text style={styles.groupName}><Ionicons name="home" size={14}/> {data.groupName}</Text>
        </View>

        <View style={styles.wowCard}>
          <View style={styles.glassLayer}>
            <Text style={styles.wowTitle}>Tu contribución mensual</Text>
            <Text style={styles.wowPoints}>{data.totalPoints}</Text>
            <Text style={styles.wowSubtitle}>puntos acumulados</Text>
          </View>
        </View>

        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <Ionicons name="flame" size={32} color="#F59E0B" />
            <Text style={styles.statValue}>{data.streak}</Text>
            <Text style={styles.statLabel}>Racha Actual</Text>
          </View>
          <View style={styles.statBox}>
            <Ionicons name="trophy" size={32} color="#10B981" />
            <Text style={styles.statValue}>{data.totalPoints}</Text>
            <Text style={styles.statLabel}>Total Global</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  scrollContent: { padding: 24 },
  noGroupContainer: { padding: 24, flex: 1, justifyContent: 'center' },
  noGroupDesc: { fontSize: 16, color: '#6B7280', marginBottom: 32, lineHeight: 24 },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 12, marginBottom: 16, fontSize:16 },
  primaryButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 12, alignItems: 'center' },
  secondaryButton: { backgroundColor: '#EEF2FF', padding: 16, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  header: { marginBottom: 32 },
  greeting: { fontSize: 32, fontWeight: '900', color: '#111827', letterSpacing: -0.5 },
  groupName: { fontSize: 16, color: '#6B7280', marginTop: 6, fontWeight:'500' },
  wowCard: { backgroundColor: '#4F46E5', borderRadius: 24, padding: 32, alignItems: 'center', marginBottom: 24 },
  glassLayer: { alignItems: 'center' },
  wowTitle: { color: '#E0E7FF', fontSize: 16, fontWeight: '600', textTransform:'uppercase', letterSpacing:1 },
  wowPoints: { color: '#fff', fontSize: 64, fontWeight: '900', marginVertical: 8 },
  wowSubtitle: { color: '#A5B4FC', fontSize: 16, fontWeight: '500' },
  statsGrid: { flexDirection: 'row', gap: 16, marginBottom: 32 },
  statBox: { flex: 1, backgroundColor: '#fff', padding: 20, borderRadius: 20, alignItems: 'center' },
  statValue: { fontSize: 24, fontWeight: 'bold', color: '#111827', marginTop: 12 },
  statLabel: { fontSize: 14, color: '#6B7280', marginTop: 4 },
  actionCard: { backgroundColor: '#fff', padding: 20, borderRadius: 20, marginBottom: 20, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 10, elevation: 2 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', color: '#111827', marginBottom: 16 },
});
