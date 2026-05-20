/**
 * Job Detail Screen — View job details and place bid
 */
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Animated,
  Platform,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RouteProp } from '@react-navigation/native';
import { Colors, Spacing, BorderRadius, FontSize, FontWeight, Shadows } from '../constants/theme';
import { submitBid } from '../services/api';
import { TechnicianStackParamList } from '../types';

type Props = {
  navigation: NativeStackNavigationProp<TechnicianStackParamList, 'JobDetail'>;
  route: RouteProp<TechnicianStackParamList, 'JobDetail'>;
};

export default function JobDetailScreen({ navigation, route }: Props) {
  const { job } = route.params;
  const [bidAmount, setBidAmount] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [bidSubmitted, setBidSubmitted] = useState(false);

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;
  const successScale = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (job.my_bid != null) {
      setBidAmount(job.my_bid.toString());
      setBidSubmitted(true);
      Animated.spring(successScale, {
        toValue: 1,
        damping: 10,
        stiffness: 80,
        useNativeDriver: true,
      }).start();
    }

    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        damping: 15,
        stiffness: 80,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const handleSubmitBid = async () => {
    const amount = parseFloat(bidAmount);
    if (!bidAmount || isNaN(amount) || amount <= 0) {
      Alert.alert('Invalid Amount', 'Please enter a valid bid amount');
      return;
    }

    setIsSubmitting(true);
    const result = await submitBid(job.id, amount);
    setIsSubmitting(false);

    if (result.error) {
      Alert.alert('Error', result.error);
      return;
    }

    setBidSubmitted(true);
    Animated.spring(successScale, {
      toValue: 1,
      damping: 10,
      stiffness: 80,
      useNativeDriver: true,
    }).start();

    setTimeout(() => {
      navigation.goBack();
    }, 2000);
  };

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#0B0F1A', '#111827']}
        style={StyleSheet.absoluteFill}
      />

      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backBtn}
          onPress={() => navigation.goBack()}
        >
          <Ionicons name="chevron-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Job #{job.id}</Text>
        <View style={styles.statusBadge}>
          <View style={[styles.statusDot, { backgroundColor: Colors.pending }]} />
          <Text style={styles.statusBadgeText}>Pending</Text>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
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
          {/* Job Details Card */}
          <View style={styles.detailCard}>
            <Text style={styles.sectionTitle}>Job Information</Text>

            <View style={styles.detailRow}>
              <View style={styles.detailIcon}>
                <Ionicons name="location" size={20} color={Colors.primary} />
              </View>
              <View style={styles.detailInfo}>
                <Text style={styles.detailLabel}>Location</Text>
                <Text style={styles.detailValue}>{job.town}, {job.city}</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.detailRow}>
              <View style={styles.detailIcon}>
                <Ionicons name="calendar" size={20} color={Colors.accent} />
              </View>
              <View style={styles.detailInfo}>
                <Text style={styles.detailLabel}>Date</Text>
                <Text style={styles.detailValue}>{job.date}</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.detailRow}>
              <View style={styles.detailIcon}>
                <Ionicons name="time" size={20} color={Colors.warning} />
              </View>
              <View style={styles.detailInfo}>
                <Text style={styles.detailLabel}>Time</Text>
                <Text style={styles.detailValue}>{job.time}</Text>
              </View>
            </View>
          </View>

          {/* Bid Section */}
          {!bidSubmitted ? (
            <View style={styles.bidCard}>
              <Text style={styles.sectionTitle}>💰 Place Your Bid</Text>
              <Text style={styles.bidSubtitle}>
                Enter your labour charge. Parts replacement costs will be discussed with the customer separately.
              </Text>

              <View style={styles.bidInputContainer}>
                <Text style={styles.currencyLabel}>Rs.</Text>
                <TextInput
                  style={styles.bidInput}
                  placeholder="0"
                  placeholderTextColor={Colors.textMuted}
                  value={bidAmount}
                  onChangeText={setBidAmount}
                  keyboardType="numeric"
                  maxLength={7}
                />
              </View>

              <View style={styles.infoBox}>
                <Ionicons name="information-circle" size={18} color={Colors.info} />
                <Text style={styles.infoText}>
                  ⚠️ Parts replacement charges will be discussed with the customer separately.
                </Text>
              </View>

              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleSubmitBid}
                disabled={isSubmitting}
                activeOpacity={0.85}
              >
                <LinearGradient
                  colors={isSubmitting ? ['#475569', '#475569'] : ['#0EA5E9', '#06D6A0']}
                  style={styles.submitGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                >
                  {isSubmitting ? (
                    <ActivityIndicator size="small" color={Colors.white} />
                  ) : (
                    <>
                      <Ionicons name="checkmark-circle" size={22} color={Colors.white} />
                      <Text style={styles.submitText}>Submit Bid</Text>
                    </>
                  )}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          ) : (
            <Animated.View
              style={[
                styles.successCard,
                { transform: [{ scale: successScale }] },
              ]}
            >
              <LinearGradient
                colors={['rgba(34, 197, 94, 0.1)', 'rgba(34, 197, 94, 0.05)']}
                style={styles.successGradient}
              >
                <View style={styles.successIcon}>
                  <Ionicons name="checkmark-circle" size={48} color={Colors.success} />
                </View>
                <Text style={styles.successTitle}>Bid Submitted! ✅</Text>
                <Text style={styles.successSubtitle}>
                  Your bid of Rs.{bidAmount} has been submitted successfully. You'll be notified if selected.
                </Text>
              </LinearGradient>
            </Animated.View>
          )}
        </Animated.View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: Platform.OS === 'ios' ? 60 : 50,
    paddingHorizontal: Spacing.xl,
    paddingBottom: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: Spacing.md,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.surfaceElevated,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    flex: 1,
    fontSize: FontSize.xl,
    fontWeight: FontWeight.bold,
    color: Colors.textPrimary,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusBadgeText: {
    fontSize: FontSize.xs,
    fontWeight: FontWeight.semibold,
    color: Colors.pending,
  },
  // Content
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: Spacing.xl,
    paddingBottom: Spacing.huge,
  },
  content: {},
  // Detail Card
  detailCard: {
    backgroundColor: Colors.surfaceElevated,
    borderRadius: BorderRadius.xl,
    padding: Spacing.xxl,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: Spacing.xl,
    ...Shadows.sm,
  },
  sectionTitle: {
    fontSize: FontSize.lg,
    fontWeight: FontWeight.bold,
    color: Colors.textPrimary,
    marginBottom: Spacing.xl,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.lg,
  },
  detailIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.surfaceHighlight,
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailInfo: {},
  detailLabel: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    fontWeight: FontWeight.medium,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  detailValue: {
    fontSize: FontSize.md,
    color: Colors.textPrimary,
    fontWeight: FontWeight.semibold,
    marginTop: 2,
  },
  divider: {
    height: 1,
    backgroundColor: Colors.borderLight,
    marginVertical: Spacing.lg,
  },
  // Bid Card
  bidCard: {
    backgroundColor: Colors.surfaceElevated,
    borderRadius: BorderRadius.xl,
    padding: Spacing.xxl,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.sm,
  },
  bidSubtitle: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    lineHeight: 20,
    marginBottom: Spacing.xxl,
    marginTop: -Spacing.md,
  },
  bidInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surfaceHighlight,
    borderRadius: BorderRadius.lg,
    borderWidth: 1.5,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.xl,
    height: 64,
    marginBottom: Spacing.lg,
  },
  currencyLabel: {
    fontSize: FontSize.xl,
    fontWeight: FontWeight.bold,
    color: Colors.primary,
    marginRight: Spacing.md,
  },
  bidInput: {
    flex: 1,
    fontSize: FontSize.xxl,
    fontWeight: FontWeight.bold,
    color: Colors.textPrimary,
  },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.sm,
    backgroundColor: 'rgba(59, 130, 246, 0.08)',
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.xxl,
  },
  infoText: {
    flex: 1,
    fontSize: FontSize.xs,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
  submitButton: {
    borderRadius: BorderRadius.lg,
    overflow: 'hidden',
    ...Shadows.md,
  },
  submitGradient: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  submitText: {
    fontSize: FontSize.lg,
    fontWeight: FontWeight.bold,
    color: Colors.white,
  },
  // Success
  successCard: {
    borderRadius: BorderRadius.xl,
    overflow: 'hidden',
    ...Shadows.md,
  },
  successGradient: {
    padding: Spacing.xxxl,
    alignItems: 'center',
    borderRadius: BorderRadius.xl,
    borderWidth: 1,
    borderColor: 'rgba(34, 197, 94, 0.2)',
  },
  successIcon: {
    marginBottom: Spacing.lg,
  },
  successTitle: {
    fontSize: FontSize.xl,
    fontWeight: FontWeight.bold,
    color: Colors.success,
    marginBottom: Spacing.sm,
  },
  successSubtitle: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
});
