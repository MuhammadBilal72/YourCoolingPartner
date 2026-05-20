/**
 * Auth Service — Token & User persistence
 */
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'ycp_auth_token';
const USER_KEY = 'ycp_user_data';

export interface UserData {
  id: number;
  name: string;
  mobile_number: string;
  role: 'user' | 'technician';
}

// ==========================================
// Token Management
// ==========================================
export async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function removeToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

// ==========================================
// User Data Management
// ==========================================
export async function saveUser(user: UserData): Promise<void> {
  await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user));
}

export async function getUser(): Promise<UserData | null> {
  const data = await SecureStore.getItemAsync(USER_KEY);
  if (data) {
    return JSON.parse(data);
  }
  return null;
}

export async function removeUser(): Promise<void> {
  await SecureStore.deleteItemAsync(USER_KEY);
}

// ==========================================
// Logout
// ==========================================
export async function logout(): Promise<void> {
  await removeToken();
  await removeUser();
}
