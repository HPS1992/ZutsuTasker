import React, { Component, ErrorInfo } from 'react';
import { Platform, StyleSheet, Text, View, ScrollView, ActivityIndicator, TouchableOpacity } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Ionicons } from '@expo/vector-icons';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { BlurView } from 'expo-blur';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import LoginScreen from './src/screens/LoginScreen';
import HomeScreen from './src/screens/HomeScreen';
import TasksScreen from './src/screens/TasksScreen';
import CalendarScreen from './src/screens/CalendarScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import MarketScreen from './src/screens/MarketScreen';
import StatsScreen from './src/screens/StatsScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

class GlobalErrorBoundary extends Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null, errorInfo: ErrorInfo | null}> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error("GlobalErrorBoundary Caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={{ flex: 1, backgroundColor: '#F8FAFC', paddingTop: 60, paddingHorizontal: 20 }}>
          <Text style={{ fontSize: 24, fontWeight: 'bold', color: '#111827', marginBottom: 20 }}>
            No se ha podido cargar la aplicación
          </Text>
          <TouchableOpacity onPress={() => this.setState({ hasError: false, error: null, errorInfo: null })}>
            <Text style={{ color: '#4F46E5', fontSize: 18, marginBottom: 20 }}>Reintentar</Text>
          </TouchableOpacity>
          {__DEV__ && (
          <ScrollView>
            <Text style={{ color: '#111827', fontSize: 16, fontWeight: 'bold', marginBottom: 10 }}>
              {this.state.error?.toString()}
            </Text>
            <Text style={{ color: '#6B7280', fontSize: 12 }}>
              {this.state.errorInfo?.componentStack}
            </Text>
          </ScrollView>
          )}
        </View>
      );
    }
    return this.props.children;
  }
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: '#5B3DF5',
        tabBarInactiveTintColor: '#94A3B8',
        tabBarStyle: {
          position: 'absolute',
          bottom: Platform.OS === 'web' ? 0 : 20,
          left: Platform.OS === 'web' ? 0 : 20,
          right: Platform.OS === 'web' ? 0 : 20,
          elevation: 0,
          backgroundColor: Platform.OS === 'web' ? '#ffffff' : 'rgba(255,255,255,0.9)',
          borderTopWidth: 0,
          height: 70,
          borderRadius: Platform.OS === 'web' ? 0 : 24,
          shadowColor: '#5B3DF5',
          shadowOffset: { width: 0, height: 10 },
          shadowOpacity: 0.1,
          shadowRadius: 20,
        },
        tabBarBackground: () => Platform.OS !== 'web' ? (
           <BlurView tint="light" intensity={80} style={[StyleSheet.absoluteFill, { borderRadius: 24, overflow: 'hidden' }]} />
        ) : null,
        tabBarShowLabel: true,
        tabBarLabelStyle: { fontWeight: 'bold', fontSize: 11, paddingBottom: 10 },
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: any = 'home';
          if (route.name === 'Tareas') iconName = focused ? 'checkbox' : 'checkbox-outline';
          else if (route.name === 'Calendario') iconName = focused ? 'calendar' : 'calendar-outline';
          else if (route.name === 'Premios') iconName = focused ? 'gift' : 'gift-outline';
          else if (route.name === 'Equidad') iconName = focused ? 'pie-chart' : 'pie-chart-outline';
          else if (route.name === 'Perfil') iconName = focused ? 'person' : 'person-outline';
          
          return <Ionicons name={iconName} size={28} color={color} style={{ marginTop: 10 }} />;
        },
      })}
    >
      <Tab.Screen name="Inicio" component={HomeScreen} />
      <Tab.Screen name="Tareas" component={TasksScreen} />
      <Tab.Screen name="Calendario" component={CalendarScreen} />
      <Tab.Screen name="Premios" component={MarketScreen} />
      <Tab.Screen name="Equidad" component={StatsScreen} />
      <Tab.Screen name="Perfil" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

function RootNavigator() {
  const { user, loading } = useAuth();
  if (loading) return <View style={{ flex: 1, justifyContent: 'center', backgroundColor: '#F8FAFC' }}><ActivityIndicator color="#4F46E5" /></View>;
  
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#F8FAFC' } }}>
      {user ? (
        <Stack.Screen name="Main" component={MainTabs} />
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} />
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <GlobalErrorBoundary>
      <SafeAreaProvider>
        <AuthProvider>
          <NavigationContainer>
            <RootNavigator />
          </NavigationContainer>
        </AuthProvider>
      </SafeAreaProvider>
    </GlobalErrorBoundary>
  );
}
