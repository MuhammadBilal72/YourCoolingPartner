/**
 * API Service — Centralized HTTP client
 */
import { API_CONFIG, ENDPOINTS } from '../constants/api';
import { getToken } from './auth';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

interface ApiResponse<T = any> {
  data: T | null;
  error: string | null;
  status: number;
}

async function request<T = any>(
  endpoint: string,
  method: HttpMethod = 'GET',
  body?: any,
  requiresAuth: boolean = true
): Promise<ApiResponse<T>> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (requiresAuth) {
      const token = await getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    const config: RequestInit = {
      method,
      headers,
    };

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);
    config.signal = controller.signal;

    const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, config);
    clearTimeout(timeoutId);

    const data = await response.json();

    if (!response.ok) {
      return {
        data: null,
        error: data.detail || `Request failed with status ${response.status}`,
        status: response.status,
      };
    }

    return { data, error: null, status: response.status };
  } catch (err: any) {
    if (err.name === 'AbortError') {
      return { data: null, error: 'Request timed out', status: 0 };
    }
    return { data: null, error: err.message || 'Network error', status: 0 };
  }
}

// ==========================================
// Auth
// ==========================================
export async function loginUser(mobile_number: string, password: string) {
  return request(ENDPOINTS.LOGIN, 'POST', { mobile_number, password }, false);
}

// ==========================================
// Chat
// ==========================================
export async function sendChatMessage(message: string) {
  return request(ENDPOINTS.CHAT, 'POST', { message });
}

export async function getChatHistory() {
  return request(ENDPOINTS.CHAT_HISTORY, 'GET');
}

// ==========================================
// Jobs
// ==========================================
export async function getJobs() {
  return request(ENDPOINTS.JOBS, 'GET');
}

export async function createJob(data: {
  city: string;
  town: string;
  date: string;
  time: string;
}) {
  return request(ENDPOINTS.JOBS, 'POST', data);
}

// ==========================================
// Bids
// ==========================================
export async function submitBid(job_id: number, amount: number) {
  return request(ENDPOINTS.BIDS, 'POST', { job_id, amount });
}

export async function getBidsForJob(jobId: number) {
  return request(ENDPOINTS.JOB_BIDS(jobId), 'GET');
}
