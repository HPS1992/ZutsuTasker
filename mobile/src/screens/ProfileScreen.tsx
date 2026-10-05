import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, Switch, TouchableOpacity, TextInput, ScrollView, Platform, Modal, Share, Alert } from 'react-native';
import { api, getMembers, transferPoints, getApiError } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { triggerWowEffect } from '../utils/SoundHaptics';
import { LinearGradient } from 'expo-linear-gradient';

export default function ProfileScreen() {
  const { logout } = useAuth();
  const [settings, setSettings] = useState<any>({ penalty_enabled: true, penalty_percentage: 50, id: '', default_assignment: 'RANDOM' });
  const [members, setMembers] = useState<any[]>([]);
  const [myStats, setMyStats] = useState<any>({});
  const [transferModal, setTransferModal] = useState(false);
  const [selectedMember, setSelectedMember] = useState<any>(null);
  const [transferAmount, setTransferAmount] = useState('');
  const [vacationMode, setVacationMode] = useState(false);

  const fetchData = () => {
    api.get('/group/settings').then(res => setSettings(res.data)).catch(()=>{});
    getMembers().then(res => setMembers(res)).catch(()=>{});
    api.get('/users/dashboard').then(res => { setMyStats(res.data); setVacationMode(res.data.is_on_vacation); }).catch(()=>{});
  };

  useEffect(() => { fetchData(); }, []);

  const changeVacationMode = async (value: boolean) => {
    const previousValue = vacationMode;
    setVacationMode(value);
    try { await api.post('/users/vacation', { is_on_vacation: value }); }
    catch (error) { setVacationMode(previousValue); Alert.alert('Error', getApiError(error)); }
  };

  const handleLogout = async () => {
    try { await logout(); }
    catch (error) { Alert.alert('Error', getApiError(error)); }
  };

  const openTransfer = (member: any) => { setSelectedMember(member); setTransferAmount(''); setTransferModal(true); };
  const handleTransfer = async () => {
    if (!transferAmount) return;
    try { await transferPoints(selectedMember.id, transferAmount); await triggerWowEffect(); setTransferModal(false); fetchData(); } 
    catch(e: any) { alert(e.response?.data?.error || 'Error'); }
  };
  const handleShareCode = async () => {
    try {
      const message = `¡Únete a mi piso en Zutsu Tasker!\nEl código es: ${settings.id}`;
      if (Platform.OS === 'web') alert(message); else await Share.share({ message });
    } catch (error) {}
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#5B3DF5', '#957CFF']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
            <Text style={styles.headerTitle}>Mi Perfil</Text>
            <Text style={styles.subtitle}>Gestión y configuración</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>

      <ScrollView contentContainerStyle={styles.content}>
        
        {/* Glowing Stats Card */}
        <LinearGradient colors={['#0F172A', '#1E293B']} style={styles.statsCard}>
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 32}}>🔥</Text>
              <Text style={styles.statsValue}>{myStats.streak || 0}</Text>
              <Text style={styles.statsLabel}>Racha Días</Text>
           </View>
           <View style={{width: 1, backgroundColor: 'rgba(255,255,255,0.1)'}} />
           <View style={{alignItems: 'center'}}>
              <Text style={{fontSize: 32}}>{myStats.is_mvp ? '👑' : '⭐'}</Text>
              <Text style={styles.statsValue}>{myStats.totalPoints || 0}</Text>
              <Text style={styles.statsLabel}>Puntos Totales</Text>
           </View>
        </LinearGradient>

        <Text style={styles.sectionTitle}>Ajustes Personales</Text>
        <View style={styles.card}>
          <View style={{flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}}>
            <View>
               <Text style={styles.settingText}>🌴 Modo Vacaciones</Text>
               <Text style={styles.helperText}>Pausa tareas temporalmente</Text>
            </View>
            <Switch value={vacationMode} onValueChange={changeVacationMode} trackColor={{true: '#F59E0B'}} />
          </View>
        </View>

        {myStats.role === 'ADMIN' && (
          <>
            <Text style={styles.sectionTitle}>Gestión del Hogar</Text>
            <View style={styles.card}>
              <TouchableOpacity onPress={handleShareCode}>
                <LinearGradient colors={['#E8DEFF', '#D3C1FF']} style={styles.inviteBtn}>
                  <Ionicons name="share-social" size={24} color="#6366F1" />
                  <Text style={styles.inviteText}>Invitar al grupo</Text>
                </LinearGradient>
              </TouchableOpacity>
              <Text style={{textAlign: 'center', marginTop: 8, color: '#94A3B8', fontWeight: 'bold', fontSize: 12}}>ID: {settings.id}</Text>
            </View>
          </>
        )}

        <Text style={styles.sectionTitle}>Mercado Negro</Text>
        <View style={styles.card}>
          {members.map((m, i) => (
            <TouchableOpacity key={m.id} style={[styles.memberRow, i < members.length-1 && {borderBottomWidth: 1, borderColor:'#F1F5F9'}]} onPress={() => openTransfer(m)} disabled={m.id === myStats.id}>
              <View>
                <Text style={styles.memberName}>{m.name} {m.is_mvp ? '👑' : ''} {m.id === myStats.id ? '(Tú)' : ''}</Text>
                <Text style={styles.memberPoints}>{m.points} pts acumulados</Text>
              </View>
              {m.id !== myStats.id && (
                <View style={styles.bribeBtn}>
                  <Text style={styles.bribeText}>Sobornar</Text>
                </View>
              )}
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
          <Text style={styles.logoutText}>Cerrar Sesión</Text>
        </TouchableOpacity>
        
        <View style={{height: 120}} />
      </ScrollView>

      <Modal visible={transferModal} animationType="slide" transparent={true}>
        <View style={{flex: 1, backgroundColor: 'rgba(15,23,42,0.8)', justifyContent: 'center', padding: 24}}>
           <View style={{backgroundColor: '#fff', padding: 32, borderRadius: 32}}>
              <Text style={{fontSize: 24, fontWeight: '900', color: '#0F172A', marginBottom: 20}}>Sobornar a {selectedMember?.name}</Text>
              <TextInput style={{backgroundColor: '#F8FAFC', padding: 20, borderRadius: 16, fontSize: 20, borderWidth: 1, borderColor: '#E2E8F0', marginBottom: 32, fontWeight: 'bold', color: '#5B3DF5'}} placeholder="Puntos a enviar..." keyboardType="numeric" value={transferAmount} onChangeText={setTransferAmount} />
              <View style={{flexDirection: 'row', justifyContent: 'flex-end', gap: 16}}>
                 <TouchableOpacity onPress={() => setTransferModal(false)} style={{padding: 16}}><Text style={{fontWeight: '700', color: '#64748B'}}>Cancelar</Text></TouchableOpacity>
                 <TouchableOpacity onPress={handleTransfer}>
                    <LinearGradient colors={['#7055F6', '#5B3DF5']} style={{paddingVertical: 16, paddingHorizontal: 32, borderRadius: 16}}>
                      <Text style={{color:'#fff', fontWeight:'800'}}>Enviar 💸</Text>
                    </LinearGradient>
                 </TouchableOpacity>
              </View>
           </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  headerGradient: { paddingBottom: 24, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, shadowColor: '#5B3DF5', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24 },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.8)', marginTop: 4, fontSize: 16, fontWeight: '500' },
  content: { padding: 20, paddingTop: 32 },
  sectionTitle: { fontSize: 13, fontWeight: '800', color: '#94A3B8', marginBottom: 12, marginLeft: 8, textTransform: 'uppercase', letterSpacing: 1 },
  statsCard: { padding: 24, borderRadius: 32, flexDirection: 'row', justifyContent: 'space-evenly', marginBottom: 32, shadowColor: '#0F172A', shadowOpacity: 0.2, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  statsValue: { color: '#fff', fontSize: 24, fontWeight: '900', marginTop: 8 },
  statsLabel: { color: '#94A3B8', fontSize: 12, fontWeight: '700', marginTop: 4, textTransform: 'uppercase' },
  card: { backgroundColor: '#fff', padding: 20, borderRadius: 24, marginBottom: 24, shadowColor: '#000', shadowOpacity: 0.02, shadowRadius: 10, elevation: 1 },
  memberRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 16 },
  memberName: { fontSize: 16, fontWeight: '800', color: '#0F172A' },
  memberPoints: { fontSize: 13, color: '#64748B', marginTop: 4, fontWeight: '600' },
  bribeBtn: { backgroundColor: '#E8DEFF', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 100 },
  bribeText: { color: '#5B3DF5', fontWeight: '800', fontSize: 13 },
  settingText: { fontSize: 16, fontWeight: '800', color: '#0F172A' },
  helperText: { fontSize: 13, color: '#64748B', marginTop: 4, fontWeight: '500' },
  inviteBtn: { padding: 20, borderRadius: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12 },
  inviteText: { color: '#5B3DF5', fontWeight: '900', fontSize: 16 },
  logoutButton: { backgroundColor: '#FEE2E2', padding: 20, borderRadius: 20, alignItems: 'center', marginTop: 16 },
  logoutText: { color: '#E11D48', fontWeight: '900', fontSize: 16, letterSpacing: 0.5 }
});
