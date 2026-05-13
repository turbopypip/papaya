import {useState, useEffect} from 'react';
import {validateAuth} from '../api/validate';
import {AUTH_CHANGED_EVENT} from '@/entities/user/lib/authEvents';

export const useValidate = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const isValid = await validateAuth();
        setIsAuthenticated(isValid);
      } catch (error) {
        console.error('Ошибка проверки аутентификации:', error);
        setIsAuthenticated(false);
      }
    };

    checkAuth();
    window.addEventListener(AUTH_CHANGED_EVENT, checkAuth);

    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, checkAuth);
    };
  }, []);

  return isAuthenticated;
};
