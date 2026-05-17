import {useState} from 'react';
import {signUpRequest} from '../api/signUp';
import {
  SignUpRequestModel,
  SignUpResponseModel,
} from '@/entities/user/types/userTypes';
import {useUserStore} from '@/entities/user';
import {getApiErrorMessage} from '@/entities/user/lib/apiError';

export const useSignUp = () => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const setUser = useUserStore(state => state.setUser);

  const signUp = async (
    data: SignUpRequestModel,
  ): Promise<SignUpResponseModel | null> => {
    try {
      setLoaded(true);
      setError(null);

      const response = await signUpRequest(data);

      setUser(response.user);
      return response;
    } catch (err: any) {
      setError(getApiErrorMessage(err, 'Ошибка регистрации'));
      return null;
    } finally {
      setLoaded(false);
    }
  };

  return {signUp, loaded, error};
};
