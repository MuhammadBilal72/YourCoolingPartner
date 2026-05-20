/**
 * Login Screen — Premium dark themed login
 * Shared by both User and Technician roles
 */
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Animated,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, BorderRadius, FontSize, FontWeight, Shadows } from '../constants/theme';
import { loginUser } from '../services/api';
import { useAuth } from '../context/AuthContext';

const { width, height } = Dimensions.get('window');

export default function LoginScreen() {
  const { login } = useAuth();
  const [mobile, setMobile] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  // Animations
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const logoScale = useRef(new Animated.Value(0.5)).current;
  const logoRotate = useRef(new Animated.Value(0)).current;
  const snowflakeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Entrance animations
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        damping: 15,
        stiffness: 80,
        useNativeDriver: true,
      }),
      Animated.spring(logoScale, {
        toValue: 1,
        damping: 10,
        stiffness: 100,
        useNativeDriver: true,
      }),
    ]).start();

    // Continuous snowflake pulse
    Animated.loop(
      Animated.sequence([
        Animated.timing(snowflakeAnim, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(snowflakeAnim, {
          toValue: 0,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  const handleLogin = async () => {
    if (!mobile.trim()) {
      Alert.alert('Error', 'Please enter your mobile number');
      return;
    }
    if (!password.trim()) {
      Alert.alert('Error', 'Please enter your password');
      return;
    }

    setIsLoading(true);
    const result = await loginUser(mobile.trim(), password);
    setIsLoading(false);

    if (result.error) {
      Alert.alert('Login Failed', result.error);
      return;
    }

    if (result.data) {
      await login(result.data.access_token, result.data.user);
    }
  };

  const snowflakeOpacity = snowflakeAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.8],
  });

  const snowflakeScale = snowflakeAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.1],
  });

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <LinearGradient
        colors={['#0B0F1A', '#0F172A', '#1E293B']}
        style={StyleSheet.absoluteFill}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
      />

      {/* Decorative circles */}
      <View style={styles.decorCircle1} />
      <View style={styles.decorCircle2} />
      <View style={styles.decorCircle3} />

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <Animated.View
          style={[
            styles.content,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          {/* Logo Section */}
          <Animated.View
            style={[
              styles.logoContainer,
              {
                transform: [{ scale: logoScale }],
              },
            ]}
          >
            <Animated.View
              style={[
                styles.logoCircle,
                {
                  opacity: snowflakeOpacity,
                  transform: [{ scale: snowflakeScale }],
                },
              ]}
            >
              <LinearGradient
                colors={['#0EA5E9', '#06D6A0']}
                style={styles.logoGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
              >
                <Text style={styles.logoIcon}>❄️</Text>
              </LinearGradient>
            </Animated.View>
            <Text style={styles.appName}>YourCoolingPartner</Text>
            <Text style={styles.tagline}>Premium AC Services at Your Doorstep</Text>
          </Animated.View>

          {/* Form Section */}
          <View style={styles.formContainer}>
            {/* Mobile Input */}
            <View
              style={[
                styles.inputContainer,
                focusedField === 'mobile' && styles.inputFocused,
              ]}
            >
              <View style={styles.inputIcon}>
                <Ionicons
                  name="call-outline"
                  size={20}
                  color={focusedField === 'mobile' ? Colors.primary : Colors.textMuted}
                />
              </View>
              <TextInput
                style={styles.input}
                placeholder="03XX XXXXXXX"
                placeholderTextColor={Colors.textMuted}
                value={mobile}
                onChangeText={setMobile}
                keyboardType="phone-pad"
                maxLength={11}
                onFocus={() => setFocusedField('mobile')}
                onBlur={() => setFocusedField(null)}
              />
            </View>

            {/* Password Input */}
            <View
              style={[
                styles.inputContainer,
                focusedField === 'password' && styles.inputFocused,
              ]}
            >
              <View style={styles.inputIcon}>
                <Ionicons
                  name="lock-closed-outline"
                  size={20}
                  color={focusedField === 'password' ? Colors.primary : Colors.textMuted}
                />
              </View>
              <TextInput
                style={styles.input}
                placeholder="Password"
                placeholderTextColor={Colors.textMuted}
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPassword}
                onFocus={() => setFocusedField('password')}
                onBlur={() => setFocusedField(null)}
              />
              <TouchableOpacity
                style={styles.eyeIcon}
                onPress={() => setShowPassword(!showPassword)}
              >
                <Ionicons
                  name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={20}
                  color={Colors.textMuted}
                />
              </TouchableOpacity>
            </View>

            {/* Login Button */}
            <TouchableOpacity
              style={styles.loginButton}
              onPress={handleLogin}
              disabled={isLoading}
              activeOpacity={0.85}
            >
              <LinearGradient
                colors={isLoading ? ['#475569', '#475569'] : ['#0EA5E9', '#06B6D4']}
                style={styles.loginGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              >
                {isLoading ? (
                  <ActivityIndicator size="small" color={Colors.white} />
                ) : (
                  <>
                    <Ionicons name="log-in-outline" size={22} color={Colors.white} />
                    <Text style={styles.loginText}>Sign In</Text>
                  </>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </View>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>
              Powered by AI • Fast & Reliable
            </Text>
          </View>
        </Animated.View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  keyboardView: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: Spacing.xxxl,
  },
  // Decorative elements
  decorCircle1: {
    position: 'absolute',
    top: -80,
    right: -60,
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(14, 165, 233, 0.06)',
  },
  decorCircle2: {
    position: 'absolute',
    bottom: 100,
    left: -80,
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: 'rgba(6, 214, 160, 0.05)',
  },
  decorCircle3: {
    position: 'absolute',
    top: height * 0.3,
    right: -40,
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: 'rgba(14, 165, 233, 0.04)',
  },
  // Logo
  logoContainer: {
    alignItems: 'center',
    marginBottom: Spacing.huge,
  },
  logoCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    marginBottom: Spacing.xl,
    ...Shadows.glow,
  },
  logoGradient: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoIcon: {
    fontSize: 44,
  },
  appName: {
    fontSize: FontSize.xxl,
    fontWeight: FontWeight.bold,
    color: Colors.textPrimary,
    letterSpacing: 0.5,
  },
  tagline: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    marginTop: Spacing.xs,
    letterSpacing: 0.3,
  },
  // Form
  formContainer: {
    gap: Spacing.lg,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surfaceElevated,
    borderRadius: BorderRadius.lg,
    borderWidth: 1.5,
    borderColor: Colors.border,
    height: 56,
    paddingHorizontal: Spacing.lg,
  },
  inputFocused: {
    borderColor: Colors.primary,
    backgroundColor: 'rgba(14, 165, 233, 0.05)',
  },
  inputIcon: {
    marginRight: Spacing.md,
  },
  input: {
    flex: 1,
    fontSize: FontSize.md,
    color: Colors.textPrimary,
    fontWeight: FontWeight.medium,
  },
  eyeIcon: {
    padding: Spacing.xs,
  },
  // Login Button
  loginButton: {
    marginTop: Spacing.sm,
    borderRadius: BorderRadius.lg,
    overflow: 'hidden',
    ...Shadows.md,
  },
  loginGradient: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  loginText: {
    fontSize: FontSize.lg,
    fontWeight: FontWeight.bold,
    color: Colors.white,
    letterSpacing: 0.5,
  },
  // Footer
  footer: {
    alignItems: 'center',
    marginTop: Spacing.huge,
  },
  footerText: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    letterSpacing: 0.5,
  },
});
