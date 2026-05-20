/**
 * API Configuration
 * Change BASE_URL to your backend server address
 */

// Use your local IP for development on a physical device
// Use 10.0.2.2 for Android Emulator, localhost for iOS Simulator
export const API_CONFIG = {
  BASE_URL: 'http://127.0.0.1:8000',
  TIMEOUT: 15000,
  POLL_INTERVAL: 10000, // 10 seconds for bid polling
};

export const ENDPOINTS = {
  LOGIN: '/auth/login',
  CHAT: '/api/chat',
  CHAT_HISTORY: '/api/chat/history',
  JOBS: '/api/jobs',
  BIDS: '/api/bids',
  JOB_BIDS: (jobId: number) => `/api/jobs/${jobId}/bids`,
};
