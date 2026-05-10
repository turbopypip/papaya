import {create} from 'zustand';
import {Thread} from '@/entities/thread/types/threadTypes';

interface ThreadState {
  threads: Thread[]; // Список тредов
  setThreads: (threads: Thread[]) => void; // Установка списка тредов
  clearThreads: () => void; // Очистка списка тредов
  addThread: (thread: Thread) => void; // Добавление нового треда
}

export const useThreadStore = create<ThreadState>(set => ({
  threads: [],

  setThreads: threads => set({threads}),
  clearThreads: () => set({threads: []}),
  addThread: thread => set(state => ({threads: [...state.threads, thread]})),
}));
