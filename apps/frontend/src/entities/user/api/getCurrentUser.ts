import {CurrentUserResponse} from '@/entities/user/types/userTypes';
import {axiosInstance} from '@/shared/api/axios';

export async function getCurrentUser(): Promise<CurrentUserResponse> {
  const response = await axiosInstance.get('/user');
  return response.data;
}
