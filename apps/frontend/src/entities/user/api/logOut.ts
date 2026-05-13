import {axiosInstance} from '@/shared/api/axios';

export async function logOutRequest(): Promise<void> {
  await axiosInstance.post('/auth/logout', undefined, {
    withCredentials: true,
  });
}
