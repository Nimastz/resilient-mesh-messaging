import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '@/components/services/apiClient';

type AppContextType = {
  user: any;
  setUser: React.Dispatch<React.SetStateAction<any>>;
  loading: boolean;
  theme: string;
  updateTheme: (newTheme: string) => Promise<void>;
  connectionStatus: string;
  setConnectionStatus: React.Dispatch<React.SetStateAction<string>>;
  loadProfile: () => Promise<void>;
};

export const AppContext = createContext<AppContextType | undefined>(undefined);


export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState('light');
  const [connectionStatus, setConnectionStatus] = useState('connected');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const profile = await apiClient.getProfile();
      if (profile) {
        setUser(profile);
        setTheme(profile.theme || 'light');
      }
    } catch (e) {
      console.error(e);
      setConnectionStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const updateTheme = async (newTheme) => {
    setTheme(newTheme);
    if (user) {
      await apiClient.updateProfile(user.id, { theme: newTheme });
      setUser(prev => ({ ...prev, theme: newTheme }));
    }
  };

  return (
    <AppContext.Provider value={{
      user,
      setUser,
      loading,
      theme,
      updateTheme,
      connectionStatus,
      setConnectionStatus,
      loadProfile
    }}>
      {children}
    </AppContext.Provider>
  );
}

export const useApp = () => useContext(AppContext);