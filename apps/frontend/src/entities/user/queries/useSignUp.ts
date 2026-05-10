import {useState} from 'react';
import {signUpRequest} from '../api/signUp';
import {SignUpRequestModel} from '@/entities/user/types/userTypes';
import {useUserStore} from '@/entities/user';

export const useSignUp = () => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setUser = useUserStore(state => state.setUser);

  const signUp = async (data: SignUpRequestModel) => {
    try {
      setLoaded(true);
      setError(null);

      // Отправляем запрос на сервер
      const response = await signUpRequest(data);

      setUser(response.user);
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || 'Ошибка регистрации';
      setError(errorMessage);
    } finally {
      setLoaded(false);
    }
  };

  return {signUp, loaded, error};
};
