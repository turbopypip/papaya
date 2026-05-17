import {axiosInstance} from '@/shared/api/axios';

export async function devLogInRequest(): Promise<void> {
  await axiosInstance.post('/auth/dev-login', undefined, {
    withCredentials: true,
  });
}
