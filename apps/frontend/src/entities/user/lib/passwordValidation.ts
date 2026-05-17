export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_REQUIREMENTS = [
  {
    id: 'minLength',
    message: `Password must be at least ${PASSWORD_MIN_LENGTH} characters long`,
    test: (password: string) => password.length >= PASSWORD_MIN_LENGTH,
  },
  {
    id: 'lowercase',
    message: 'Password must include a lowercase Latin letter',
    test: (password: string) => /[a-z]/.test(password),
  },
  {
    id: 'uppercase',
    message: 'Password must include an uppercase Latin letter',
    test: (password: string) => /[A-Z]/.test(password),
  },
  {
    id: 'number',
    message: 'Password must include a number',
    test: (password: string) => /\d/.test(password),
  },
  {
    id: 'special',
    message: 'Password must include a special character',
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
