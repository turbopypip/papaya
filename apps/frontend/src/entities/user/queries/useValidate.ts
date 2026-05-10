import {useState, useEffect} from 'react';
import {validateAuth} from '../api/validate';

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
  }, []);

  return isAuthenticated;
};
