import {useState, useEffect} from 'react';
import {validateAuth} from '../api/validate';
import {AUTH_CHANGED_EVENT} from '@/entities/user/lib/authEvents';
import {IS_DEV_MODE} from '@/shared/env';
import {isDevAutoLoginDisabled} from '@/entities/user/lib/authEvents';
import {devLogInRequest} from '@/entities/user/api/devLogIn';
import {completeAuthSuccess} from '@/entities/user/lib/authSuccess';
import {useQueryClient} from '@tanstack/react-query';

export const useValidate = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    let isMounted = true;

    const checkAuth = async () => {
      try {
        const isValid = await validateAuth();
        if (isMounted) {
          setIsAuthenticated(isValid);
        }
      } catch (error) {
        if (IS_DEV_MODE && !isDevAutoLoginDisabled()) {
          try {
            await devLogInRequest();
            await completeAuthSuccess(queryClient);
            if (isMounted) {
              setIsAuthenticated(true);
            }
            return;
          } catch {
            // Fall through to unauthenticated state.
          }
        }

        if (isMounted) {
          setIsAuthenticated(false);
        }
      }
    };

    checkAuth();
    window.addEventListener(AUTH_CHANGED_EVENT, checkAuth);

    return () => {
      isMounted = false;
      window.removeEventListener(AUTH_CHANGED_EVENT, checkAuth);
    };
  }, [queryClient]);

  return isAuthenticated;
};
