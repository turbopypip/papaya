import {axiosInstance} from '@/shared/api/axios';
import {emitAuthChanged} from '@/entities/user/lib/authEvents';

export async function logOutRequest(): Promise<void> {
  await axiosInstance.post('/auth/logout', undefined, {
    withCredentials: true,
  });
  emitAuthChanged();
}
