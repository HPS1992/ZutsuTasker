import React, { useState } from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, Dimensions } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width } = Dimensions.get('window');

const SLIDES = [
  { id: '1', title: 'Bienvenido a Zutsu', desc: 'El método japonés para dividir las tareas del hogar de forma justa y transparente.', icon: 'home' },
  { id: '2', title: 'Equidad Total', desc: 'Olvídate de las discusiones. Descubre quién hace qué con nuestra barra de equilibrio.', icon: 'pie-chart' },
  { id: '3', title: 'Gana Recompensas', desc: 'Convierte el esfuerzo en premios. Canjea puntos por librarte de fregar o cenas pagadas.', icon: 'gift' },
  { id: '4', title: 'Cero Retrasos', desc: 'Mantén tu racha. Las tareas olvidadas restan puntos al cabo de 2 días.', icon: 'flame' }
];

export default function OnboardingScreen() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const navigation = useNavigation<any>();

  const nextSlide = async () => {
    if (currentIndex < SLIDES.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else {
      await AsyncStorage.setItem('hasSeenOnboarding', 'true');
      navigation.replace('Auth');
    }
  };

  const slide = SLIDES[currentIndex];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.iconContainer}>
          <Ionicons name={slide.icon as any} size={100} color="#4F46E5" />
        </View>
        <Text style={styles.title}>{slide.title}</Text>
        <Text style={styles.desc}>{slide.desc}</Text>
      </View>
      <View style={styles.footer}>
        <View style={styles.dots}>
          {SLIDES.map((_, i) => (
            <View key={i} style={[styles.dot, currentIndex === i && styles.activeDot]} />
          ))}
        </View>
        <TouchableOpacity style={styles.button} onPress={nextSlide}>
          <Text style={styles.buttonText}>{currentIndex === SLIDES.length - 1 ? 'Empezar' : 'Siguiente'}</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  iconContainer: { width: 160, height: 160, backgroundColor: '#EEF2FF', borderRadius: 80, alignItems: 'center', justifyContent: 'center', marginBottom: 40 },
  title: { fontSize: 32, fontWeight: '900', color: '#111827', marginBottom: 16, textAlign: 'center' },
  desc: { fontSize: 18, color: '#6B7280', textAlign: 'center', lineHeight: 28 },
  footer: { padding: 32, paddingBottom: 48 },
  dots: { flexDirection: 'row', justifyContent: 'center', marginBottom: 32 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#E5E7EB', marginHorizontal: 6 },
  activeDot: { backgroundColor: '#4F46E5', width: 24 },
  button: { backgroundColor: '#4F46E5', padding: 20, borderRadius: 16, alignItems: 'center' },
  buttonText: { color: '#fff', fontSize: 18, fontWeight: 'bold' }
});
