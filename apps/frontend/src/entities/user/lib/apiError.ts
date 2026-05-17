import axios from 'axios';

type ErrorResponse = {
  error?: string;
  message?: string;
  details?: string[] | string;
  description?: string;
};

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError<ErrorResponse>(error)) {
    return fallback;
  }

  const data = error.response?.data;
  if (!data) {
    return fallback;
  }

  if (Array.isArray(data.details) && data.details.length > 0) {
    return data.details.join('. ');
  }

  return data.error || data.message || data.description || fallback;
}
