import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,

      setAuth: (user, token, refreshToken) => set({ user, token, refreshToken: refreshToken ?? get().refreshToken }),
      setUser: (user) => set({ user }),
      logout: () => set({ user: null, token: null, refreshToken: null }),
      updateUser: (updates) => set((s) => ({ user: s.user ? { ...s.user, ...updates } : null })),

      isAuthenticated: () => !!get().token,
      isPremium: () => ['premium', 'admin'].includes(get().user?.role),
      isAdmin: () => get().user?.role === 'admin',
    }),
    {
      name: 'xithsense-auth',
      partialize: (s) => ({ user: s.user, token: s.token, refreshToken: s.refreshToken }),
    },
  ),
)
