import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, FlatList, ActivityIndicator, Platform } from 'react-native';
import { getEquityStats } from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';

export default function StatsScreen() {
  const [stats, setStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { getEquityStats().then(setStats).finally(() => setLoading(false)); }, []);

  const renderItem = ({ item, index }: any) => {
    const isFirst = index === 0;
    return (
      <View style={[styles.card, isFirst && styles.firstCard]}>
        <View style={styles.cardHeader}>
          <Text style={[styles.name, isFirst && {color:'#fff'}]}>{isFirst ? '👑 ' : ''}{item.name}</Text>
          <Text style={[styles.percentage, isFirst && {color:'#fff'}]}>{item.percentage}%</Text>
        </View>
        <View style={styles.barContainer}>
          {isFirst ? (
             <LinearGradient colors={['#FCD34D', '#F59E0B']} style={[styles.bar, { width: `${item.percentage}%` }]} />
          ) : (
             <LinearGradient colors={['#10B981', '#059669']} style={[styles.bar, { width: `${item.percentage}%` }]} />
          )}
        </View>
        <Text style={[styles.details, isFirst && {color:'rgba(255,255,255,0.8)'}]}>Lleva {item.points} puntos globales generados en la casa</Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#5B3DF5', '#957CFF']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
             <Text style={styles.headerTitle}>Equidad</Text>
             <Text style={styles.subtitle}>¿Quién se está escaqueando?</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>

      {loading ? <ActivityIndicator style={{marginTop: 50}} color="#6366F1"/> : (
        <FlatList data={stats.sort((a,b)=>b.points-a.points)} renderItem={renderItem} keyExtractor={i => i.name} contentContainerStyle={styles.list} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  headerGradient: { paddingBottom: 32, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 40, borderBottomRightRadius: 40, shadowColor: '#5B3DF5', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24 },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.7)', marginTop: 4, fontSize: 16, fontWeight: '600' },
  list: { padding: 20, paddingTop: 32, paddingBottom: 100 },
  card: { backgroundColor: '#fff', padding: 24, borderRadius: 32, marginBottom: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 15, elevation: 2, borderWidth: 1, borderColor: '#F1F5F9' },
  firstCard: { backgroundColor: '#5B3DF5', shadowColor: '#5B3DF5', shadowOpacity: 0.3, borderColor: '#5B3DF5' },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20, alignItems: 'center' },
  name: { fontSize: 20, fontWeight: '900', color: '#0F172A' },
  percentage: { fontSize: 24, fontWeight: '900', color: '#0F172A' },
  barContainer: { height: 16, backgroundColor: 'rgba(0,0,0,0.06)', borderRadius: 100, overflow: 'hidden', marginBottom: 12 },
  bar: { height: '100%', borderRadius: 100 },
  details: { fontSize: 13, color: '#64748B', fontWeight: '600' }
});
