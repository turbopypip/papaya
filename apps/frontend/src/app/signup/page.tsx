'use client';
import React, {useState} from 'react';
import {Box, Button, Card, Input, Stack} from '@chakra-ui/react';
import {Field} from '@/shared/Components/Field/ui/field';
import styles from './styles.module.css';
import {SignUpRequestModel} from '@/entities/user/types/userTypes';
import {useSignUp} from '@/entities/user/queries/useSignUp';
import {PasswordInput} from '@/shared/components/PasswordInput/ui/password-input';
import {useRouter} from 'next/navigation';
const SignUp = () => {
  const [form, setForm] = useState<SignUpRequestModel>({
    username: '',
    email: '',
    password: '',
    roleId: '1ef94a6d-ed65-6cd0-bfb7-718b8878121a',
  });

  const router = useRouter();

  const {signUp, loaded, error} = useSignUp();

  const handleSubmit = () => {
    signUp(form);
  };

  const handleCancel = () => {
    setForm({
      username: '',
      email: '',
      password: '',
      roleId: '1ef94a6d-ed65-6cd0-bfb7-718b8878121a',
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

  return (
    <Box className={styles.cardContainer}>
      <Card.Root maxW="sm">
        <Card.Header>
          <Card.Title>Sign up</Card.Title>
          <Card.Description>
            Fill in the form below to create an account
          </Card.Description>
        </Card.Header>
        <Card.Body>
          <Stack gap="4" w="full">
            <Field label="Username">
              <Input
                name="username"
                value={form.username}
                onChange={handleChange}
              />
            </Field>
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
            Sign up
          </Button>
        </Card.Footer>
      </Card.Root>
    </Box>
  );
};

export default SignUp;
