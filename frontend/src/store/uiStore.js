import { create } from 'zustand'
import { persist } from 'zustand/middleware'

let toastId = 0

/** Toasts + theme + upgrade prompt. */
export const useUiStore = create(
  persist(
    (set, get) => ({
      theme: 'dark',
      toasts: [],
      upgrade: null, // { feature, message } when an upgrade modal should show

      setTheme: (theme) => {
        document.documentElement.dataset.theme = theme
        set({ theme })
      },
      toggleTheme: () => get().setTheme(get().theme === 'dark' ? 'light' : 'dark'),

      toast: (t) => {
        const id = ++toastId
        const item = { id, type: 'info', ...t }
        set((s) => ({ toasts: [...s.toasts.slice(-3), item] }))
        setTimeout(() => get().dismiss(id), t.duration || 4200)
        return id
      },
      dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) })),

      showUpgrade: (upgrade) => set({ upgrade }),
      hideUpgrade: () => set({ upgrade: null }),
    }),
    { name: 'xithsense-ui', partialize: (s) => ({ theme: s.theme }) },
  ),
)

export const toast = {
  success: (title, message) => useUiStore.getState().toast({ type: 'success', title, message }),
  error: (title, message) => useUiStore.getState().toast({ type: 'error', title, message }),
  info: (title, message) => useUiStore.getState().toast({ type: 'info', title, message }),
}
