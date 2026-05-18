'use client';
import React from 'react';
import {Box, Button, Card, Input, Stack, Text} from '@chakra-ui/react';
import {Field} from '@/shared/Components/Field/ui/field';
import styles from './styles.module.css';
import {SignUpRequestModel} from '@/entities/user/types/userTypes';
import {useSignUp} from '@/entities/user/queries/useSignUp';
import {
  PasswordInput,
  PasswordStrengthMeter,
} from '@/shared/Components/PasswordInput/ui/password-input';
import {useRouter} from 'next/navigation';
import {useForm} from 'react-hook-form';
import {z} from 'zod';
import {zodResolver} from '@hookform/resolvers/zod';
import {
  getPasswordStrength,
  getPasswordValidationErrors,
  isStrongPassword,
  PASSWORD_REQUIREMENTS,
} from '@/entities/user/lib/passwordValidation';

const signupSchema = z
  .object({
    username: z.string().trim().min(1, 'Введите имя пользователя'),
    email: z
      .string()
      .trim()
      .min(1, 'Введите email')
      .email('Введите корректный email'),
    password: z.string().superRefine((password, ctx) => {
      if (isStrongPassword(password)) {
        return;
      }

      ctx.addIssue({
        code: 'custom',
        message: getPasswordValidationErrors(password).join('. '),
      });
    }),
    confirmPassword: z.string().min(1, 'Повторите пароль'),
  })
  .refine(data => data.password === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Пароли не совпадают',
  });

type SignUpFormValues = z.infer<typeof signupSchema>;

const SignUp = () => {
  const router = useRouter();

  const {signUp, loaded, error} = useSignUp();
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: {errors, isValid},
  } = useForm<SignUpFormValues>({
    resolver: zodResolver(signupSchema),
    mode: 'onChange',
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  });

  const password = watch('password');
  const passwordStrength = getPasswordStrength(password);

  const onSubmit = async (values: SignUpFormValues) => {
    const data: SignUpRequestModel = {
      username: values.username,
      email: values.email,
      password: values.password,
    };

    const response = await signUp(data);
    if (response != null) {
      router.push('/');
    }
  };

  const handleCancel = () => {
    reset();
    router.push('/');
  };

  return (
    <Box className={styles.cardContainer}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Card.Root maxW="md">
          <Card.Header>
            <Card.Title>Регистрация</Card.Title>
            <Card.Description>
              Заполните форму, чтобы создать аккаунт
            </Card.Description>
          </Card.Header>
          <Card.Body>
            <Stack gap="4" w="full">
              <Field
                label="Имя пользователя"
                invalid={Boolean(errors.username)}
                errorText={errors.username?.message}>
                <Input autoComplete="username" {...register('username')} />
              </Field>
              <Field
                label="Email"
                invalid={Boolean(errors.email)}
                errorText={errors.email?.message}>
                <Input
                  type="email"
                  autoComplete="email"
                  {...register('email')}
                />
              </Field>
              <Field
                label="Пароль"
                invalid={Boolean(errors.password)}
                errorText={errors.password?.message}
                helperText={
                  password ? (
                    <Stack gap="2" width="full">
                      <PasswordStrengthMeter
                        max={PASSWORD_REQUIREMENTS.length}
                        value={passwordStrength}
                      />
                      <Text textStyle="xs">
                        Используйте минимум 8 символов: строчную и заглавную
                        латинские буквы, цифру и специальный символ.
                      </Text>
                    </Stack>
                  ) : null
                }>
                <PasswordInput
                  autoComplete="new-password"
                  placeholder="Придумайте пароль"
                  {...register('password')}
                />
              </Field>
              <Field
                label="Повторите пароль"
                invalid={Boolean(errors.confirmPassword)}
                errorText={errors.confirmPassword?.message}>
                <PasswordInput
                  autoComplete="new-password"
                  placeholder="Повторите пароль"
                  {...register('confirmPassword')}
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
            <Button variant="solid" disabled={loaded || !isValid} type="submit">
              {loaded ? 'Регистрируем...' : 'Зарегистрироваться'}
            </Button>
          </Card.Footer>
        </Card.Root>
      </form>
    </Box>
  );
};

export default SignUp;
