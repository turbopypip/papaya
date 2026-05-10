import {useState} from 'react';
import {logInRequest} from '../api/logIn';
import {LogInRequestModel} from '@/entities/user/types/userTypes';

export const useLogIn = () => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const logIn = async (data: LogInRequestModel) => {
    try {
      setLoaded(true);
      setError(null);

      // Отправляем запрос на сервер
      const response = await logInRequest(data);

      if (response.error) {
        console.log(new Error(response.error));
      }
    } catch (err: any) {
      console.log(err);
      const errorMessage = err.response?.data?.error || 'Ошибка входа';
      setError(errorMessage);
    } finally {
      setLoaded(true);
    }
  };

  return {logIn, loaded, error};
};
