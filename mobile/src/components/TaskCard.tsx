import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform, Alert, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTaskStore } from '../store/useTaskStore';
import { LinearGradient } from 'expo-linear-gradient';

export const TaskCard = ({ item, currentUserId, onComplete, onEdit }: any) => {
  const { claimTask, stealTask, approveTask } = useTaskStore();
  const assignedUserId = typeof item.assigned_to === 'string' ? item.assigned_to : item.assigned_to?.id;
  const isMine = assignedUserId === currentUserId;
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
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          {onEdit && (
            <TouchableOpacity onPress={onEdit} style={styles.editBtn}>
              <Ionicons name="pencil" size={16} color="#64748B" />
            </TouchableOpacity>
          )}
          <View style={[styles.pointsBadge, hasBounty && styles.bountyBadge]}>
            <Text style={[styles.pointsText, hasBounty && styles.bountyText]}>{hasBounty ? '🔥' : '⭐'} {displayPoints} pts</Text>
          </View>
        </View>
      </View>

      <View style={styles.detailsRow}>
        <View style={[styles.infoChip, {backgroundColor: '#E8DEFF', borderColor: '#D3C1FF'}]}>
           <Ionicons name={item.template.room_icon || 'home'} size={14} color="#4F46E5" />
           <Text style={[styles.infoText, {color: '#5B3DF5'}]}>{item.template.room_name || 'General'}</Text>
        </View>
        <View style={styles.infoChip}><Ionicons name="calendar-outline" size={14} color="#64748B" /><Text style={styles.infoText}>{new Date(item.due_date).toLocaleDateString()}</Text></View>
        {item.assigned_to ? (
          <View style={styles.infoChip}><Ionicons name="person-circle-outline" size={16} color="#64748B" /><Text style={[styles.infoText, isMine && {color: '#5B3DF5', fontWeight: 'bold'}]}>{isMine ? 'Tuya' : item.assigned_to.name}</Text></View>
        ) : (
          <View style={[styles.infoChip, { backgroundColor: '#FEF3C7', borderColor: '#FCD34D' }]}><Ionicons name="hand-right-outline" size={14} color="#D97706" /><Text style={[styles.infoText, {color: '#D97706', fontWeight: 'bold'}]}>¡Libre!</Text></View>
        )}
      </View>

      <View style={styles.actions}>
        {item.status === 'PENDING' && !item.assigned_to && (
          <TouchableOpacity onPress={handleClaim} style={{ flex: 1 }}><LinearGradient colors={['#7055F6', '#5B3DF5']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>¡Me la pido!</Text></LinearGradient></TouchableOpacity>
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
            {!isMine && <TouchableOpacity onPress={handleApprove} style={{ flex: 1 }}><LinearGradient colors={['#A28CFF', '#5B3DF5']} style={styles.primaryButton}><Text style={styles.primaryButtonText}>✅ Aprobar</Text></LinearGradient></TouchableOpacity>}
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
  iconBox: { backgroundColor: '#E8DEFF', padding: 10, borderRadius: 16, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 18, fontWeight: '800', color: '#0F172A', flexWrap: 'wrap', marginRight: 8 },
  photoRequiredText: { fontSize: 12, color: '#DB2777', fontWeight: 'bold', marginTop: 2 },
  pointsBadge: { backgroundColor: '#FEF3C7', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  bountyBadge: { backgroundColor: '#FEE2E2' },
  pointsText: { color: '#B45309', fontWeight: '900', fontSize: 14 },
  bountyText: { color: '#E11D48' },
  editBtn: { backgroundColor: '#F1F5F9', padding: 8, borderRadius: 12 },
  detailsRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  infoChip: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#F8FAFC', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, borderColor: '#F1F5F9' },
  infoText: { color: '#64748B', fontSize: 13, fontWeight: '600' },
  actions: { flexDirection: 'row', gap: 10 },
  primaryButton: { paddingVertical: 14, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  primaryButtonText: { color: '#fff', fontWeight: '800', fontSize: 15, letterSpacing: 0.5 },
});
