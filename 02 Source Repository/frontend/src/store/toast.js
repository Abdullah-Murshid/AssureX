import { create } from 'zustand'

let nextId = 1

export const useToast = create((set, get) => ({
  toasts: [],

  push: (message, type = 'success', ttl = 5000) => {
    const id = nextId++
    set((state) => ({ toasts: [...state.toasts, { id, message, type }] }))
    if (ttl) {
      setTimeout(() => get().dismiss(id), ttl)
    }
    return id
  },

  dismiss: (id) =>
    set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
}))
