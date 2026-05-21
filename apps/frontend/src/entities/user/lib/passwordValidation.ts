export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_REQUIREMENTS = [
  {
    id: 'minLength',
    message: `Пароль должен быть не короче ${PASSWORD_MIN_LENGTH} символов`,
    test: (password: string) => password.length >= PASSWORD_MIN_LENGTH,
  },
  {
    id: 'lowercase',
    message: 'Пароль должен содержать строчную латинскую букву',
    test: (password: string) => /[a-z]/.test(password),
  },
  {
    id: 'uppercase',
    message: 'Пароль должен содержать заглавную латинскую букву',
    test: (password: string) => /[A-Z]/.test(password),
  },
  {
    id: 'number',
    message: 'Пароль должен содержать цифру',
    test: (password: string) => /\d/.test(password),
  },
  {
    id: 'special',
    message: 'Пароль должен содержать специальный символ',
    test: (password: string) => /[^A-Za-z0-9]/.test(password),
  },
] as const;

export function getPasswordValidationErrors(password: string): string[] {
  return PASSWORD_REQUIREMENTS.filter(rule => !rule.test(password)).map(
    rule => rule.message,
  );
}

export function isStrongPassword(password: string): boolean {
  return getPasswordValidationErrors(password).length === 0;
}

export function getPasswordStrength(password: string): number {
  if (!password) {
    return 0;
  }

  return PASSWORD_REQUIREMENTS.filter(rule => rule.test(password)).length;
}
