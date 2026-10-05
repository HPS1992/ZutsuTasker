import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, SafeAreaView, Alert } from 'react-native';
import { useAuth } from '../context/AuthContext';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const { login, register } = useAuth();

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
      <View style={styles.formContainer}>
        <Text style={styles.header}>Zutsu Tasker</Text>
        <Text style={styles.subHeader}>{isRegistering ? 'Únete al equipo' : 'El equilibrio empieza en casa'}</Text>

        {isRegistering && (
          <TextInput style={styles.input} placeholder="Tu nombre" value={name} onChangeText={setName} />
        )}
        <TextInput style={styles.input} placeholder="Correo electrónico" autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} />
        <TextInput style={styles.input} placeholder="Contraseña" secureTextEntry value={password} onChangeText={setPassword} />

        <TouchableOpacity style={styles.primaryButton} onPress={handleSubmit}>
          <Text style={styles.primaryButtonText}>{isRegistering ? 'Crear Cuenta' : 'Iniciar Sesión'}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton} onPress={() => setIsRegistering(!isRegistering)}>
          <Text style={styles.secondaryButtonText}>
            {isRegistering ? 'Ya tengo cuenta, iniciar sesión' : 'Crear una cuenta nueva'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  formContainer: { flex: 1, justifyContent: 'center', padding: 24 },
  header: { fontSize: 32, fontWeight: 'bold', color: '#1F2937', textAlign: 'center' },
  subHeader: { fontSize: 16, color: '#6B7280', textAlign: 'center', marginBottom: 40 },
  input: { backgroundColor: '#F3F4F6', padding: 16, borderRadius: 10, marginBottom: 16, fontSize: 16 },
  primaryButton: { backgroundColor: '#4F46E5', padding: 16, borderRadius: 10, alignItems: 'center', marginTop: 8 },
  primaryButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  secondaryButton: { padding: 16, alignItems: 'center', marginTop: 8 },
  secondaryButtonText: { color: '#4F46E5', fontSize: 16, fontWeight: '600' },
});
