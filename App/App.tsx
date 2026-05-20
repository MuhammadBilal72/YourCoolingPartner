/**
 * YourCoolingPartner — React Native App
 * Root entry point with Auth Provider and Navigation
 */
import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider } from './src/context/AuthContext';
import AppNavigator from './src/navigation/AppNavigator';

export default function App() {
  return (
    <AuthProvider>
      <StatusBar style="light" translucent backgroundColor="transparent" />
      <AppNavigator />
    </AuthProvider>
  );
}
