import React, {useState} from 'react';
import {Button, Container, Flex, Link} from '@chakra-ui/react';
import styles from './styles.module.css';
import {useRouter} from 'next/navigation';
import {useValidate} from '@/entities/user/queries/useValidate';
import {devLogInRequest} from '@/entities/user/api/devLogIn';
import {logOutRequest} from '@/entities/user/api/logOut';
import {disableDevAutoLogin} from '@/entities/user/lib/authEvents';
import {useUserStore} from '@/entities/user';
import {IS_DEV_MODE} from '@/shared/env';
import {useQueryClient} from '@tanstack/react-query';
import {completeAuthSuccess} from '@/entities/user/lib/authSuccess';

const Navbar = () => {
  const isAuthenticated = useValidate();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isDevLoggingIn, setIsDevLoggingIn] = useState(false);
  const clearUser = useUserStore(state => state.clearUser);
  const queryClient = useQueryClient();
  const router = useRouter();
  const handleClickRouting = (path: string) => {
    router.push(`/${path}`);
  };

  const handleLogOut = async () => {
    setIsLoggingOut(true);
    disableDevAutoLogin();

    try {
      await logOutRequest();
      clearUser();
      router.push('/');
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleDevLogIn = async () => {
    setIsDevLoggingIn(true);

    try {
      await devLogInRequest();
      await completeAuthSuccess(queryClient);
      router.push('/');
    } finally {
      setIsDevLoggingIn(false);
    }
  };

  return (
    <Container className={styles.navbar}>
      <Flex direction="row" justify="space-between">
        <Link href="/" className={styles.logo}>
          Papaya
        </Link>
        {isAuthenticated ? (
          <Flex gap={5} align="center">
            <Button onClick={handleLogOut} disabled={isLoggingOut}>
              {isLoggingOut ? 'Выходим...' : 'Выйти'}
            </Button>
          </Flex>
        ) : (
          <Flex gap={5} align="center">
            <Button onClick={() => handleClickRouting('signup')}>
              Регистрация
            </Button>
            <Button onClick={() => handleClickRouting('login')}>Войти</Button>
            {IS_DEV_MODE ? (
              <Button onClick={handleDevLogIn} disabled={isDevLoggingIn}>
                {isDevLoggingIn ? 'Входим...' : 'Войти как dev-пользователь'}
              </Button>
            ) : null}
          </Flex>
        )}
      </Flex>
    </Container>
  );
};

export default Navbar;
