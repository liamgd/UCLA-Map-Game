import { create } from "zustand";

export const useStore = create((set) => ({
  selectedId: null,
  setSelectedId: (id) => set({ selectedId: id }),
  query: "",
  setQuery: (q) => set({ query: q }),
  activeIndex: -1,
  setActiveIndex: (n) => set({ activeIndex: n }),
}));

