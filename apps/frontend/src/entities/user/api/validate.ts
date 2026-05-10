import {axiosInstance} from '@/shared/api/axios';

export async function validateAuth(): Promise<boolean> {
  const response = await axiosInstance.get('/auth/validate', {
    withCredentials: true,
  });

  return response.status === 200;
}
