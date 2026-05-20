/**
 * App Navigation — Role-based routing
 * Login → User Chat / Technician Home
 */
import React from 'react';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Colors } from '../constants/theme';
import { useAuth } from '../context/AuthContext';

// Screens
import LoginScreen from '../screens/LoginScreen';
import UserChatScreen from '../screens/UserChatScreen';
import TechHomeScreen from '../screens/TechHomeScreen';
import JobListScreen from '../screens/JobListScreen';
import JobDetailScreen from '../screens/JobDetailScreen';
import MyBookingsScreen from '../screens/MyBookingsScreen';
import NotificationsScreen from '../screens/NotificationsScreen';

// Types
import { RootStackParamList, TechnicianStackParamList } from '../types';

const RootStack = createNativeStackNavigator<RootStackParamList>();
const TechStack = createNativeStackNavigator<TechnicianStackParamList>();

// Dark Navigation Theme
const DarkNavTheme = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    primary: Colors.primary,
    background: Colors.background,
    card: Colors.surface,
    text: Colors.textPrimary,
    border: Colors.border,
    notification: Colors.primary,
  },
};

// Technician Navigator
function TechnicianNavigator() {
  return (
    <TechStack.Navigator
      screenOptions={{
        headerShown: false,
        animation: 'slide_from_right',
        contentStyle: { backgroundColor: Colors.background },
      }}
    >
      <TechStack.Screen name="TechHome" component={TechHomeScreen} />
      <TechStack.Screen name="JobList" component={JobListScreen} />
      <TechStack.Screen name="JobDetail" component={JobDetailScreen} />
      <TechStack.Screen name="MyBookings" component={MyBookingsScreen} />
      <TechStack.Screen name="Notifications" component={NotificationsScreen} />
    </TechStack.Navigator>
  );
}

// Loading screen
function LoadingScreen() {
  return (
    <View style={styles.loadingContainer}>
      <ActivityIndicator size="large" color={Colors.primary} />
    </View>
  );
}

export default function AppNavigator() {
  const { isLoggedIn, isLoading, user } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <NavigationContainer theme={DarkNavTheme}>
      <RootStack.Navigator
        screenOptions={{
          headerShown: false,
          animation: 'fade',
          contentStyle: { backgroundColor: Colors.background },
        }}
      >
        {!isLoggedIn ? (
          <RootStack.Screen name="Login" component={LoginScreen} />
        ) : user?.role === 'technician' ? (
          <RootStack.Screen name="TechnicianApp" component={TechnicianNavigator} />
        ) : (
          <RootStack.Screen name="UserApp" component={UserChatScreen} />
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
