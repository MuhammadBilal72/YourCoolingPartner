/**
 * Type definitions for the app
 */

// ==========================================
// Navigation Types
// ==========================================
export type RootStackParamList = {
  Login: undefined;
  UserApp: undefined;
  TechnicianApp: undefined;
};

export type TechnicianStackParamList = {
  TechHome: undefined;
  JobList: undefined;
  JobDetail: { job: Job };
  MyBookings: undefined;
  Notifications: undefined;
};

// ==========================================
// API Response Types
// ==========================================
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    name: string;
    mobile_number: string;
    role: 'user' | 'technician';
  };
}

export interface ChatMessage {
  id?: number;
  sender: 'user' | 'agent';
  content: string;
  timestamp?: string;
  isLoading?: boolean;
  loadingStep?: number;
}

export interface ChatHistoryResponse {
  conversation_id: number | null;
  messages: ChatMessage[];
}

export interface ChatResponse {
  response: string;
  action: string;
}

export interface Job {
  id: number;
  user_id: number;
  city: string;
  town: string;
  status: string;
  date: string;
  time: string;
  my_bid?: number | null;
}

export interface Bid {
  id: number;
  technician_id: number;
  technician_name?: string;
  amount: number;
}

export interface Notification {
  id: number;
  content: string;
  is_read: boolean;
  created_at: string;
}
