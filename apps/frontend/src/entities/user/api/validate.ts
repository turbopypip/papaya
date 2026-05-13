import {axiosInstance} from '@/shared/api/axios';
import {isDevAutoLoginDisabled} from '@/entities/user/lib/authEvents';
import {IS_DEV_MODE} from '@/shared/env';

export async function validateAuth(): Promise<boolean> {
  try {
    const response = await axiosInstance.get('/auth/validate', {
      withCredentials: true,
    });

    return response.status === 200;
  } catch (error) {
    if (!IS_DEV_MODE || isDevAutoLoginDisabled()) {
      throw error;
    }

    const {devLogInRequest} = await import('@/entities/user/api/devLogIn');
    await devLogInRequest();
    return true;
  }
}
