'use client';
import React, {useState} from 'react';
import styles from '@/app/signup/styles.module.css';
import {Box, Button, Card, Input, Stack, Text} from '@chakra-ui/react';
import {Field} from '@/shared/Components/Field/ui/field';
import {PasswordInput} from '@/shared/Components/PasswordInput/ui/password-input';
import {LogInRequestModel} from '@/entities/user';
import {useRouter} from 'next/navigation';
import {useLogIn} from '@/entities/user/queries/useLogIn';

const Login = () => {
  const [form, setForm] = useState<LogInRequestModel>({
    email: '',
    password: '',
  });
  const router = useRouter();
  const {logIn, loaded, error} = useLogIn();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      await logIn(form);
      router.replace('/');
    } catch {
      // Текст ошибки отображается из состояния mutation.
    }
  };

  const handleCancel = () => {
    setForm({
      email: '',
      password: '',
    });
    router.push('/');
  };
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const {name, value} = e.target;
    setForm(prev => ({...prev, [name]: value}));
  };

  return (
    <Box className={styles.cardContainer}>
      <form onSubmit={handleSubmit}>
        <Card.Root maxW="sm">
          <Card.Header>
            <Card.Title>Вход</Card.Title>
            <Card.Description>
              Введите email и пароль, чтобы войти в аккаунт
            </Card.Description>
          </Card.Header>
          <Card.Body>
            <Stack gap="4" w="full">
              <Field label="Email">
                <Input
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={handleChange}
                />
              </Field>
              <Field label="Пароль">
                <PasswordInput
                  name="password"
                  autoComplete="current-password"
                  placeholder="Введите пароль"
                  value={form.password}
                  onChange={handleChange}
                />
              </Field>
              {error ? (
                <Text color="red.500" textStyle="sm">
                  {error}
                </Text>
              ) : null}
            </Stack>
          </Card.Body>
          <Card.Footer justifyContent="flex-end">
            <Button variant="outline" onClick={handleCancel}>
              Отмена
            </Button>
            <Button
              variant="solid"
              type="submit"
              disabled={loaded || !form.email || !form.password}>
              {loaded ? 'Входим...' : 'Войти'}
            </Button>
          </Card.Footer>
        </Card.Root>
      </form>
    </Box>
  );
};

export default Login;
