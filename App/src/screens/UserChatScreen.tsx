/**
 * User Chat Screen — The single-screen experience
 * Handles: chat, loading animations, bid polling, booking
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  Animated,
  KeyboardAvoidingView,
  Platform,
  Dimensions,
  ActivityIndicator,
  Image,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Spacing, BorderRadius, FontSize, FontWeight, Shadows } from '../constants/theme';
import { sendChatMessage, getChatHistory, getJobs, getBidsForJob } from '../services/api';
import { API_CONFIG } from '../constants/api';
import { useAuth } from '../context/AuthContext';
import { ChatMessage, Job, Bid } from '../types';

const { width } = Dimensions.get('window');
const LOGO_IMAGE = require('../../assets/logo.png');

const LOADING_STEPS = [
  '🔍 Understanding your requirement...',
  '🗺️ Finding nearest technicians...',
  '🏆 Ranking best matches...',
];

// ==========================================
// Chat Bubble Component
// ==========================================
function ChatBubble({ message, index }: { message: ChatMessage; index: number }) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(20)).current;
  const dotAnim = useRef(new Animated.Value(0)).current;

  const isUser = message.sender === 'user';
  const isLoading = message.isLoading;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        delay: index * 50,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        damping: 20,
        stiffness: 120,
        delay: index * 50,
        useNativeDriver: true,
      }),
    ]).start();

    if (isLoading) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(dotAnim, {
            toValue: 1,
            duration: 600,
            useNativeDriver: true,
          }),
          Animated.timing(dotAnim, {
            toValue: 0,
            duration: 600,
            useNativeDriver: true,
          }),
        ])
      ).start();
    }
  }, []);

  const dotOpacity = dotAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 1],
  });

  return (
    <Animated.View
      style={[
        styles.bubbleRow,
        isUser ? styles.bubbleRowUser : styles.bubbleRowAgent,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      {/* Avatar for agent */}
      {!isUser && (
        <View style={styles.avatarContainer}>
          <LinearGradient
            colors={['#0EA5E9', '#06D6A0']}
            style={styles.avatar}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          >
            <Text style={styles.avatarText}>❄️</Text>
          </LinearGradient>
        </View>
      )}

      <View
        style={[
          styles.bubble,
          isUser ? styles.bubbleUser : styles.bubbleAgent,
          isLoading && styles.bubbleLoading,
        ]}
      >
        {isLoading ? (
          <View style={styles.loadingContent}>
            <Animated.Text
              style={[styles.loadingText, { opacity: dotOpacity }]}
            >
              {message.content}
            </Animated.Text>
          </View>
        ) : (
          <Text
            style={[
              styles.bubbleText,
              isUser ? styles.bubbleTextUser : styles.bubbleTextAgent,
            ]}
          >
            {message.content}
          </Text>
        )}
      </View>

      {/* Avatar for user */}
      {isUser && (
        <View style={styles.avatarContainer}>
          <View style={styles.avatarUser}>
            <Ionicons name="person" size={16} color={Colors.primary} />
          </View>
        </View>
      )}
    </Animated.View>
  );
}

// ==========================================
// Main Chat Screen
// ==========================================
export default function UserChatScreen() {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const flatListRef = useRef<FlatList>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inputAnim = useRef(new Animated.Value(0)).current;

  // Load chat history on mount
  useEffect(() => {
    loadHistory();
    checkForPendingJobs();
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Animate input bar
  useEffect(() => {
    Animated.timing(inputAnim, {
      toValue: 1,
      duration: 500,
      delay: 300,
      useNativeDriver: true,
    }).start();
  }, []);

  const loadHistory = async () => {
    setIsLoadingHistory(true);
    const result = await getChatHistory();
    if (result.data?.messages?.length) {
      setMessages(result.data.messages);
    } else {
      setMessages([]);
    }
    setIsLoadingHistory(false);
  };

  const checkForPendingJobs = async () => {
    const result = await getJobs();
    if (result.data) {
      const pendingJobs = result.data.filter((j: Job) => j.status === 'pending');
      if (pendingJobs.length > 0) {
        startBidPolling(pendingJobs[0].id);
      }
    }
  };

  const startBidPolling = (jobId: number) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    let lastBidCount = 0;

    pollIntervalRef.current = setInterval(async () => {
      const result = await getBidsForJob(jobId);
      if (result.data && result.data.length > lastBidCount) {
        const newBids = result.data.slice(lastBidCount);
        lastBidCount = result.data.length;

        const bidText = newBids
          .map((b: Bid, i: number) => `${i + 1}. ${b.technician_name || `Technician #${b.technician_id}`} — Labour: Rs.${b.amount}`)
          .join('\n');

        const bidMessage: ChatMessage = {
          sender: 'agent',
          content: `🔔 ${newBids.length} new bid(s) received!\n\n${bidText}\n\nKisko book karein? Bus naam likh dein.`,
        };
        setMessages((prev) => [...prev, bidMessage]);
      }
    }, API_CONFIG.POLL_INTERVAL);
  };

  const showLoadingAnimation = (): Promise<void> => {
    return new Promise(async (resolve) => {
      for (let i = 0; i < LOADING_STEPS.length; i++) {
        const loadingMsg: ChatMessage = {
          sender: 'agent',
          content: LOADING_STEPS[i],
          isLoading: true,
          loadingStep: i,
        };
        setMessages((prev) => [...prev, loadingMsg]);
        await new Promise((r) => setTimeout(r, 800));
      }
      resolve();
    });
  };

  const removeLoadingMessages = () => {
    setMessages((prev) => prev.filter((m) => !m.isLoading));
  };

  const handleSend = async () => {
    if (!inputText.trim() || isSending) return;

    const userMessage: ChatMessage = {
      sender: 'user',
      content: inputText.trim(),
    };
    setMessages((prev) => [...prev, userMessage]);
    const messageText = inputText.trim();
    setInputText('');
    setIsSending(true);

    // Show loading animation
    const loadingPromise = showLoadingAnimation();

    // Send to API
    const result = await sendChatMessage(messageText);
    await loadingPromise;

    // Remove loading bubbles and show real response
    removeLoadingMessages();

    if (result.error) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          content: `⚠️ Sorry, something went wrong. Please try again.\n\n(${result.error})`,
        },
      ]);
    } else if (result.data) {
      let finalContent = result.data.response;

      if (
        result.data.action === 'search_technicians' &&
        result.data.found_technicians &&
        result.data.found_technicians.length > 0 &&
        result.data.response.includes('\n')
      ) {
        const techsText = result.data.found_technicians
          .map((t: any) => `Name: ${t.name}\nMobile: ${t.mobile_number}\nAddress: ${t.address || 'N/A'}`)
          .join('\n------------------\n');

        finalContent += `\n\n🌟 Here are list of technicans found IN our system:\n\n${techsText}\n------------------`;
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: 'agent',
          content: finalContent,
        },
      ]);

      // If a job was created, start polling
      if (result.data.action === 'create_job') {
        checkForPendingJobs();
      }
    }

    setIsSending(false);
  };

  const scrollToEnd = () => {
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  useEffect(() => {
    scrollToEnd();
  }, [messages]);

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <LinearGradient
        colors={['#0B0F1A', '#111827']}
        style={StyleSheet.absoluteFill}
      />

      {/* Header */}
      <View style={styles.header}>
        <LinearGradient
          colors={['rgba(14, 165, 233, 0.1)', 'transparent']}
          style={styles.headerGradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
        >
          <View style={styles.headerContent}>
            <View style={styles.headerLeft}>
              <View style={styles.headerLogo}>
                <Image source={LOGO_IMAGE} style={styles.headerLogoImage} />
              </View>
              <View>
                <Text style={styles.headerTitle}>YourCoolingPartner</Text>
                <View style={styles.onlineIndicator}>
                  <View style={styles.onlineDot} />
                  <Text style={styles.onlineText}>AI Assistant Online</Text>
                </View>
              </View>
            </View>
            <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
              <Ionicons name="log-out-outline" size={22} color={Colors.textSecondary} />
            </TouchableOpacity>
          </View>
        </LinearGradient>
      </View>

      {/* Chat Messages */}
      {isLoadingHistory ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingHistoryText}>Loading conversations...</Text>
        </View>
      ) : (
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(_, index) => `msg-${index}`}
          renderItem={({ item, index }) => (
            <ChatBubble message={item} index={index} />
          )}
          ListEmptyComponent={
            <View style={styles.emptyChatContainer}>
              <Image source={LOGO_IMAGE} style={styles.emptyChatLogo} />
              <Text style={styles.emptyChatTitle}>YourCoolingPartner</Text>
              <Text style={styles.emptyChatText}>
                Send a simple message to book your technician.
              </Text>
            </View>
          }
          contentContainerStyle={styles.chatList}
          showsVerticalScrollIndicator={false}
          onContentSizeChange={scrollToEnd}
        />
      )}

      {/* Input Bar */}
      <Animated.View
        style={[
          styles.inputBar,
          {
            opacity: inputAnim,
            transform: [
              {
                translateY: inputAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [30, 0],
                }),
              },
            ],
          },
        ]}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
        >
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.textInput}
              placeholder="Type a message..."
              placeholderTextColor={Colors.textMuted}
              value={inputText}
              onChangeText={setInputText}
              multiline
              maxLength={500}
              editable={!isSending}
            />
            <TouchableOpacity
              style={[
                styles.sendButton,
                (!inputText.trim() || isSending) && styles.sendButtonDisabled,
              ]}
              onPress={handleSend}
              disabled={!inputText.trim() || isSending}
              activeOpacity={0.7}
            >
              <LinearGradient
                colors={
                  inputText.trim() && !isSending
                    ? ['#0EA5E9', '#06D6A0']
                    : ['#334155', '#334155']
                }
                style={styles.sendGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
              >
                {isSending ? (
                  <ActivityIndicator size="small" color={Colors.white} />
                ) : (
                  <Ionicons name="send" size={18} color={Colors.white} />
                )}
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Animated.View>
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
    paddingTop: Platform.OS === 'ios' ? 50 : 40,
  },
  headerGradient: {
    paddingBottom: Spacing.md,
    paddingHorizontal: Spacing.xl,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  headerLogo: {
    width: 42,
    height: 42,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
    ...Shadows.glow,
  },
  headerLogoImage: {
    width: 42,
    height: 42,
  },
  headerTitle: {
    fontSize: FontSize.lg,
    fontWeight: FontWeight.bold,
    color: Colors.textPrimary,
  },
  onlineIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  onlineDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.success,
  },
  onlineText: {
    fontSize: FontSize.xs,
    color: Colors.success,
  },
  logoutBtn: {
    padding: Spacing.sm,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.surfaceElevated,
  },
  // Loading
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.md,
  },
  loadingHistoryText: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
  },
  // Chat List
  chatList: {
    flexGrow: 1,
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.md,
  },
  emptyChatContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
  },
  emptyChatLogo: {
    width: 112,
    height: 112,
    marginBottom: Spacing.lg,
  },
  emptyChatTitle: {
    fontSize: FontSize.xxl,
    fontWeight: FontWeight.extrabold,
    color: Colors.textPrimary,
    textAlign: 'center',
    marginBottom: Spacing.sm,
  },
  emptyChatText: {
    fontSize: FontSize.md,
    lineHeight: 22,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
  // Bubble Row
  bubbleRow: {
    flexDirection: 'row',
    marginBottom: Spacing.md,
    alignItems: 'flex-end',
    gap: Spacing.sm,
  },
  bubbleRowUser: {
    justifyContent: 'flex-end',
  },
  bubbleRowAgent: {
    justifyContent: 'flex-start',
  },
  // Avatar
  avatarContainer: {
    marginBottom: 2,
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 16,
  },
  avatarUser: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.primaryMuted,
    justifyContent: 'center',
    alignItems: 'center',
  },
  // Bubble
  bubble: {
    maxWidth: width * 0.72,
    padding: Spacing.md,
    borderRadius: BorderRadius.xl,
  },
  bubbleUser: {
    backgroundColor: Colors.primary,
    borderBottomRightRadius: BorderRadius.xs,
    ...Shadows.sm,
  },
  bubbleAgent: {
    backgroundColor: Colors.surfaceElevated,
    borderBottomLeftRadius: BorderRadius.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  bubbleLoading: {
    backgroundColor: 'rgba(14, 165, 233, 0.08)',
    borderColor: 'rgba(14, 165, 233, 0.2)',
  },
  bubbleText: {
    fontSize: FontSize.md,
    lineHeight: 22,
  },
  bubbleTextUser: {
    color: Colors.white,
  },
  bubbleTextAgent: {
    color: Colors.textPrimary,
  },
  loadingContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: FontSize.sm,
    color: Colors.primary,
    fontWeight: FontWeight.medium,
  },
  // Input Bar
  inputBar: {
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.surface,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    paddingBottom: Platform.OS === 'ios' ? Spacing.xxxl : Spacing.md,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Spacing.sm,
  },
  textInput: {
    flex: 1,
    backgroundColor: Colors.surfaceElevated,
    borderRadius: BorderRadius.xl,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    fontSize: FontSize.md,
    color: Colors.textPrimary,
    maxHeight: 100,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  sendButton: {
    borderRadius: BorderRadius.full,
    overflow: 'hidden',
  },
  sendButtonDisabled: {
    opacity: 0.5,
  },
  sendGradient: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
