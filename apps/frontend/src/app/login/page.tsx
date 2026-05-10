'use client';
import React, {useState} from 'react';
import styles from '@/app/signup/styles.module.css';
import {Box, Button, Card, Input, Stack} from '@chakra-ui/react';
import {Field} from '@/shared/Components/Field/ui/field';
import {PasswordInput} from '@/shared/Components/PasswordInput/ui/password-input';
import {LogInRequestModel} from '@/entities/user';
import {useRouter} from 'next/navigation';
import {useSignUp} from '@/entities/user/queries/useSignUp';
import {useLogIn} from '@/entities/user/queries/useLogIn';

const Login = () => {
  const [form, setForm] = useState<LogInRequestModel>({
    email: '',
    password: '',
  });
  const router = useRouter();
  const {logIn, loaded, error} = useLogIn();

  const handleSubmit = () => {
    logIn(form);
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

  if (loaded && error != null) {
    return <div>{error}</div>;
  }
  if (loaded && error == null) {
    router.push('/');
  }

  return (
    <Box className={styles.cardContainer}>
      <Card.Root maxW="sm">
        <Card.Header>
          <Card.Title>Log in</Card.Title>
          <Card.Description>
            Fill in the form below to log in an account
          </Card.Description>
        </Card.Header>
        <Card.Body>
          <Stack gap="4" w="full">
            <Field label="Email">
              <Input name="email" value={form.email} onChange={handleChange} />
            </Field>
            <Field label="Password">
              <PasswordInput
                name="password"
                value={form.password}
                onChange={handleChange}
              />
            </Field>
          </Stack>
        </Card.Body>
        <Card.Footer justifyContent="flex-end">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button variant="solid" onClick={handleSubmit}>
            Log in
          </Button>
        </Card.Footer>
      </Card.Root>
    </Box>
  );
};

export default Login;
