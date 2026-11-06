import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
  Animated,
  Image,
  ActivityIndicator,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { LinearGradient } from 'expo-linear-gradient';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const { login, register } = useAuth();

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.7)).current;
  const floatAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Animación de entrada suave con rebote elástico
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 6,
        tension: 40,
        useNativeDriver: true,
      }),
    ]).start();

    // Levitación continua del logo (flotación vertical suave)
    Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, {
          toValue: -12,
          duration: 1800,
          useNativeDriver: true,
        }),
        Animated.timing(floatAnim, {
          toValue: 0,
          duration: 1800,
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Efecto de respiración/pulso del halo luminoso
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.08,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const handleSubmit = async () => {
    try {
      if (isRegistering) {
        if (!name) return Alert.alert('Error', 'El nombre es obligatorio');
        await register(email, password, name);
      } else {
        await login(email, password);
      }
    } catch (err: any) {
      Alert.alert('Error', err.response?.data?.error || err.message);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Animated.View style={[styles.formContainer, { opacity: fadeAnim }]}>
        
        {/* Logo con halo radiante y levitación */}
        <View style={styles.logoWrapper}>
          <Animated.View
            style={[
              styles.glowRing,
              {
                transform: [
                  { translateY: floatAnim },
                  { scale: pulseAnim },
                ],
              },
            ]}
          />
          <Animated.View
            style={{
              transform: [
                { scale: scaleAnim },
                { translateY: floatAnim },
              ],
            }}
          >
            <Image
              source={require('../../assets/icon.png')}
              style={styles.logoImage}
              resizeMode="cover"
            />
          </Animated.View>
        </View>

        <Text style={styles.header}>Zutsu Tasker</Text>
        <Text style={styles.subHeader}>
          {isRegistering ? 'Únete al equipo' : 'El equilibrio empieza en casa'}
        </Text>

        {isRegistering && (
          <TextInput
            style={styles.input}
            placeholder="Tu nombre"
            placeholderTextColor="#94A3B8"
            value={name}
            onChangeText={setName}
          />
        )}
        <TextInput
          style={styles.input}
          placeholder="Correo electrónico"
          placeholderTextColor="#94A3B8"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="Contraseña"
          placeholderTextColor="#94A3B8"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity style={{ marginTop: 8 }} onPress={handleSubmit}>
          <LinearGradient colors={['#7055F6', '#5B3DF5']} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>
              {isRegistering ? 'Crear Cuenta' : 'Iniciar Sesión'}
            </Text>
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() => setIsRegistering(!isRegistering)}
        >
          <Text style={styles.secondaryButtonText}>
            {isRegistering
              ? 'Ya tengo cuenta, iniciar sesión'
              : 'Crear una cuenta nueva'}
          </Text>
        </TouchableOpacity>
      </Animated.View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8FAFC' },
  formContainer: { flex: 1, justifyContent: 'center', padding: 32 },
  logoWrapper: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    height: 140,
  },
  glowRing: {
    position: 'absolute',
    width: 130,
    height: 130,
    borderRadius: 40,
    backgroundColor: '#7055F6',
    opacity: 0.25,
    shadowColor: '#5B3DF5',
    shadowOpacity: 0.6,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 12 },
  },
  logoImage: {
    width: 110,
    height: 110,
    borderRadius: 32,
    borderWidth: 2,
    borderColor: '#EDE9FE',
  },
  header: {
    fontSize: 38,
    fontWeight: '900',
    color: '#0F172A',
    textAlign: 'center',
    letterSpacing: -1,
    marginTop: 8,
  },
  subHeader: {
    fontSize: 15,
    color: '#64748B',
    textAlign: 'center',
    marginBottom: 36,
    fontWeight: '500',
  },
  input: {
    backgroundColor: '#fff',
    padding: 18,
    borderRadius: 18,
    marginBottom: 14,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    color: '#0F172A',
    fontWeight: '500',
    shadowColor: '#000',
    shadowOpacity: 0.02,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  primaryButton: {
    padding: 18,
    borderRadius: 18,
    alignItems: 'center',
    shadowColor: '#5B3DF5',
    shadowOpacity: 0.35,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
  },
  primaryButtonText: { color: '#fff', fontSize: 17, fontWeight: '800' },
  secondaryButton: { padding: 18, alignItems: 'center', marginTop: 8 },
  secondaryButtonText: { color: '#64748B', fontSize: 15, fontWeight: '700' },
});
