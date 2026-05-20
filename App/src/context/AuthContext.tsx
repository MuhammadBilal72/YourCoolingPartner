/**
 * Auth Context — Global authentication state
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserData, getUser, getToken, saveToken, saveUser, logout as authLogout } from '../services/auth';

interface AuthContextType {
  user: UserData | null;
  token: string | null;
  isLoading: boolean;
  isLoggedIn: boolean;
  login: (token: string, user: UserData) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  isLoggedIn: false,
  login: async () => {},
  logout: async () => {},
});

export const useAuth = () => useContext(AuthContext);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserData | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadStoredAuth();
  }, []);

  async function loadStoredAuth() {
    try {
      const [storedToken, storedUser] = await Promise.all([
        getToken(),
        getUser(),
      ]);
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(storedUser);
      }
    } catch (err) {
      console.error('Failed to load auth:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function login(newToken: string, newUser: UserData) {
    await saveToken(newToken);
    await saveUser(newUser);
    setToken(newToken);
    setUser(newUser);
  }

  async function logout() {
    await authLogout();
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isLoggedIn: !!token && !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
