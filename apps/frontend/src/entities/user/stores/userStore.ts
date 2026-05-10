import {create} from 'zustand';
import {User} from '@/entities/user/types/userTypes';

interface UserState {
  user: User | null;
  setUser: (user: User) => void;
  clearUser: () => void;
}

export const useUserStore = create<UserState>(set => ({
  user: null, // Начальное состояние пользователя

  setUser: user => set({user}), // Установка пользователя
  clearUser: () => set({user: null}), // Очистка состояния пользователя
}));
