import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, ScrollView, Alert } from 'react-native';
import { Calendar, LocaleConfig } from 'react-native-calendars';
import { LinearGradient } from 'expo-linear-gradient';
import { Platform } from 'react-native';
import { useTaskStore } from '../store/useTaskStore';
import { TaskCard } from '../components/TaskCard';
import { useAuth } from '../context/AuthContext';
import { getApiError } from '../services/api';
import * as ImagePicker from 'expo-image-picker';

LocaleConfig.locales['es'] = {
  monthNames: ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'],
  monthNamesShort: ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'],
  dayNames: ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'],
  dayNamesShort: ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'],
  today: 'Hoy'
};
LocaleConfig.defaultLocale = 'es';

export default function CalendarScreen({ navigation }: any) {
  const { tasks, fetchTasks, completeTask, error } = useTaskStore();
  const { user } = useAuth();
  const currentUserId = user?.id || user?.uid;
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => { fetchTasks(); }, []);

  const handleComplete = async (task: any) => {
    try {
      if (task.template.requires_photo) {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) return Alert.alert('Permiso necesario', 'Permite el acceso a la cámara para fotografiar la tarea.');
        const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.5 });
        if (result.canceled || !result.assets?.[0]?.uri) return;
        await completeTask(task.id, result.assets[0].uri);
      } else {
        await completeTask(task.id);
      }
    } catch (error) { Alert.alert('Error', getApiError(error)); }
  };

  const getMarkedDates = () => {
    const marks: any = {};
    tasks.forEach(t => {
      const date = new Date(t.due_date).toISOString().split('T')[0];
      marks[date] = { marked: true, dotColor: t.status === 'COMPLETED' ? '#10B981' : '#5B3DF5' };
    });
    marks[selectedDate] = { ...marks[selectedDate], selected: true, selectedColor: '#5B3DF5' };
    return marks;
  };

  const tasksForDate = tasks.filter(t => new Date(t.due_date).toISOString().split('T')[0] === selectedDate);

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#5B3DF5', '#957CFF']} style={styles.headerGradient}>
        <SafeAreaView>
          <View style={styles.headerContent}>
            <Text style={styles.headerTitle}>Calendario</Text>
            <Text style={styles.subtitle}>Planificación mensual</Text>
          </View>
        </SafeAreaView>
      </LinearGradient>
      <ScrollView contentContainerStyle={{ paddingBottom: 120 }}>
        <Calendar
          current={selectedDate}
          onDayPress={(day: any) => setSelectedDate(day.dateString)}
          markedDates={getMarkedDates()}
          theme={{
            todayTextColor: '#5B3DF5',
            selectedDayBackgroundColor: '#5B3DF5',
            arrowColor: '#5B3DF5',
          }}
        />
        <View style={styles.tasksSection}>
          {error && <Text style={{ color: '#B91C1C', marginBottom: 12 }}>{error}</Text>}
          <Text style={styles.sectionTitle}>Tareas del {selectedDate}</Text>
          {tasksForDate.length === 0 ? (
            <Text style={styles.emptyText}>No hay tareas para este día.</Text>
          ) : (
            tasksForDate.map(t => (
              <View key={t.id} style={{marginBottom: 12}}>
                 {/* Envuelto en touchable para ir a detalles si se quiere */}
                 <TaskCard item={t} currentUserId={currentUserId} onComplete={() => handleComplete(t)} />
              </View>
            ))
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F3F4F6' },
  
  headerGradient: { paddingBottom: 24, paddingTop: Platform.OS === 'android' ? 40 : 0, borderBottomLeftRadius: 32, borderBottomRightRadius: 32, shadowColor: '#5B3DF5', shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: {width: 0, height: 10} },
  headerContent: { paddingHorizontal: 24 },
  headerTitle: { fontSize: 32, fontWeight: '900', color: '#fff', letterSpacing: -1 },
  subtitle: { color: 'rgba(255,255,255,0.8)', marginTop: 4, fontSize: 16, fontWeight: '500' },

  tasksSection: { padding: 16 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#374151' },
  emptyText: { color: '#6B7280', fontStyle: 'italic', textAlign: 'center', marginTop: 20 }
});
