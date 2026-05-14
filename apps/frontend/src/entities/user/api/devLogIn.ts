import {axiosInstance} from '@/shared/api/axios';
import {emitAuthChanged} from '@/entities/user/lib/authEvents';

export async function devLogInRequest(): Promise<void> {
  await axiosInstance.post('/auth/dev-login', undefined, {
    withCredentials: true,
  });
  emitAuthChanged();
}
