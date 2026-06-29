import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,

      setAuth: (user, token, refreshToken) => set({ user, token, refreshToken }),

      logout: () => set({ user: null, token: null, refreshToken: null }),

      updateUser: (updates) => set((state) => ({
        user: state.user ? { ...state.user, ...updates } : null,
      })),

      isAuthenticated: () => !!get().token,
      isPremium: () => get().user?.role === 'premium' || get().user?.role === 'admin',
      isAdmin: () => get().user?.role === 'admin',
    }),
    {
      name: 'xithsense-auth',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
    }
  )
)
