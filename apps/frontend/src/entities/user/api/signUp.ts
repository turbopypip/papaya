import {axiosInstance} from '@/shared/api/axios';
import {
  SignUpRequestModel,
  SignUpResponseModel,
} from '@/entities/user/types/userTypes';
import {AxiosResponse} from 'axios';

export async function signUpRequest(
  data: SignUpRequestModel,
): Promise<SignUpResponseModel> {
  const response = (await axiosInstance.post(
    '/auth/signup',
    data,
  )) as AxiosResponse<SignUpResponseModel>;

  return response.data;
}
