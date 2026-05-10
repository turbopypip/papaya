import React from 'react';
import {Button, Container, Flex, IconButton, Link} from '@chakra-ui/react';
import {LuSearch} from 'react-icons/lu';
import styles from './styles.module.css';
import {useRouter} from 'next/navigation';
import {useValidate} from '@/entities/user/queries/useValidate';

const Navbar = () => {
  const isAuthenticated = useValidate();
  const router = useRouter();
  const handleClickRouting = (path: string) => {
    router.push(`/${path}`);
  };

  return (
    <Container className={styles.navbar}>
      <Flex direction="row" justify="space-between">
        <Link href="/" className={styles.logo}>
          Papaya
        </Link>
        {!isAuthenticated ? (
          <Flex gap={5} align="center">
            <Button onClick={() => handleClickRouting('signup')}>
              Sign up
            </Button>
            <Button onClick={() => handleClickRouting('login')}>Log in</Button>
          </Flex>
        ) : (
          <Flex gap={5} align="center">
            <Button onClick={() => handleClickRouting('signup')}>
              Create new account
            </Button>
            <Button onClick={() => handleClickRouting('login')}>Log in</Button>
          </Flex>
        )}
      </Flex>
    </Container>
  );
};

export default Navbar;
