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
    username: z.string().trim().min(1, 'Username is required'),
    email: z
      .string()
      .trim()
      .min(1, 'Email is required')
      .email('Enter a valid email'),
    password: z.string().superRefine((password, ctx) => {
      if (isStrongPassword(password)) {
        return;
      }

      ctx.addIssue({
        code: 'custom',
        message: getPasswordValidationErrors(password).join('. '),
      });
    }),
    confirmPassword: z.string().min(1, 'Confirm your password'),
  })
  .refine(data => data.password === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Passwords do not match',
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
            <Card.Title>Sign up</Card.Title>
            <Card.Description>
              Fill in the form below to create an account
            </Card.Description>
          </Card.Header>
          <Card.Body>
            <Stack gap="4" w="full">
              <Field
                label="Username"
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
                label="Password"
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
                        Use at least 8 characters with uppercase, lowercase,
                        number, and special character.
                      </Text>
                    </Stack>
                  ) : null
                }>
                <PasswordInput
                  autoComplete="new-password"
                  placeholder="Create password"
                  {...register('password')}
                />
              </Field>
              <Field
                label="Confirm password"
                invalid={Boolean(errors.confirmPassword)}
                errorText={errors.confirmPassword?.message}>
                <PasswordInput
                  autoComplete="new-password"
                  placeholder="Repeat password"
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
              Cancel
            </Button>
            <Button variant="solid" disabled={loaded || !isValid} type="submit">
              {loaded ? 'Signing up...' : 'Sign up'}
            </Button>
          </Card.Footer>
        </Card.Root>
      </form>
    </Box>
  );
};

export default SignUp;
