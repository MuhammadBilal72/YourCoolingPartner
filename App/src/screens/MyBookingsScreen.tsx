/**
 * My Bookings Screen — Technician's confirmed bookings
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  RefreshControl,
  Animated,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { Colors, Spacing, BorderRadius, FontSize, FontWeight, Shadows } from '../constants/theme';
import { getJobs } from '../services/api';
import { TechnicianStackParamList, Job } from '../types';

type Props = {
  navigation: NativeStackNavigationProp<TechnicianStackParamList, 'MyBookings'>;
};

function BookingCard({ job, index }: { job: Job; index: number }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 400,
        delay: index * 120,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        damping: 15,
        stiffness: 100,
        delay: index * 120,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const isActive = job.status === 'active' || job.status === 'booked';

  return (
    <Animated.View
      style={[
        styles.bookingCard,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      <View style={styles.bookingContent}>
        {/* Status indicator */}
        <View style={styles.statusStrip}>
          <LinearGradient
            colors={isActive ? ['#22C55E', '#16A34A'] : ['#64748B', '#475569']}
            style={styles.statusStripGradient}
          />
        </View>

        <View style={styles.bookingBody}>
          {/* Status badge */}
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: isActive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(100, 116, 139, 0.1)' },
            ]}
          >
            <View
              style={[
                styles.statusDot,
                { backgroundColor: isActive ? Colors.success : Colors.textMuted },
              ]}
            />
            <Text
              style={[
                styles.statusText,
                { color: isActive ? Colors.success : Colors.textMuted },
              ]}
            >
              {isActive ? 'Active' : job.status}
            </Text>
          </View>

          {/* Details */}
          <View style={styles.bookingRow}>
            <Ionicons name="location-outline" size={16} color={Colors.primary} />
            <Text style={styles.bookingValue}>{job.town}, {job.city}</Text>
          </View>

          <View style={styles.bookingRow}>
            <Ionicons name="calendar-outline" size={16} color={Colors.accent} />
            <Text style={styles.bookingValue}>
              {job.date} • {job.time}
            </Text>
          </View>
        </View>
      </View>
    </Animated.View>
  );
}

export default function MyBookingsScreen({ navigation }: Props) {
  const [bookings, setBookings] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchBookings = useCallback(async () => {
    const result = await getJobs();
    if (result.data) {
      // Show all non-pending jobs (booked/active ones)
      setBookings(result.data.filter((j: Job) => j.status !== 'pending'));
    }
  }, []);

  useEffect(() => {
    loadBookings();
  }, []);

  const loadBookings = async () => {
    setIsLoading(true);
    await fetchBookings();
    setIsLoading(false);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchBookings();
    setRefreshing(false);
  };

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <View style={styles.emptyIcon}>
        <Ionicons name="calendar-outline" size={48} color={Colors.textMuted} />
      </View>
      <Text style={styles.emptyTitle}>No Bookings Yet</Text>
      <Text style={styles.emptySubtitle}>
        Your confirmed bookings will appear here. Start by bidding on available jobs!
      </Text>
    </View>
  );

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
        <Text style={styles.headerTitle}>My Bookings</Text>
        <View style={styles.countBadge}>
          <Text style={styles.countText}>{bookings.length}</Text>
        </View>
      </View>

      {isLoading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading bookings...</Text>
        </View>
      ) : (
        <FlatList
          data={bookings}
          keyExtractor={(item) => `booking-${item.id}`}
          renderItem={({ item, index }) => (
            <BookingCard job={item} index={index} />
          )}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={renderEmpty}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={Colors.primary}
              colors={[Colors.primary]}
            />
          }
        />
      )}
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
  countBadge: {
    backgroundColor: Colors.accentMuted,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
  },
  countText: {
    fontSize: FontSize.sm,
    fontWeight: FontWeight.bold,
    color: Colors.accent,
  },
  // Loading
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.md,
  },
  loadingText: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
  },
  // List
  listContent: {
    padding: Spacing.xl,
    paddingBottom: Spacing.huge,
    flexGrow: 1,
  },
  // Booking Card
  bookingCard: {
    marginBottom: Spacing.lg,
    borderRadius: BorderRadius.xl,
    backgroundColor: Colors.surfaceElevated,
    borderWidth: 1,
    borderColor: Colors.border,
    overflow: 'hidden',
    ...Shadows.sm,
  },
  bookingContent: {
    flexDirection: 'row',
  },
  statusStrip: {
    width: 4,
  },
  statusStripGradient: {
    flex: 1,
  },
  bookingBody: {
    flex: 1,
    padding: Spacing.xl,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 6,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
    marginBottom: Spacing.md,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusText: {
    fontSize: FontSize.xs,
    fontWeight: FontWeight.semibold,
  },
  bookingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.sm,
  },
  bookingValue: {
    fontSize: FontSize.md,
    color: Colors.textPrimary,
    fontWeight: FontWeight.medium,
  },
  // Empty State
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xxxl,
    paddingTop: Spacing.massive,
  },
  emptyIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.surfaceElevated,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.xl,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  emptyTitle: {
    fontSize: FontSize.lg,
    fontWeight: FontWeight.bold,
    color: Colors.textPrimary,
    marginBottom: Spacing.sm,
  },
  emptySubtitle: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
});
