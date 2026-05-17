import {axiosInstance} from '@/shared/api/axios';
import {
  LogInRequestModel,
  LogInResponseModel,
} from '@/entities/user/types/userTypes';
import {AxiosResponse} from 'axios';

export async function logInRequest(
  data: LogInRequestModel,
): Promise<LogInResponseModel> {
  const response = (await axiosInstance.post(
    '/auth/login',
    data,
  )) as AxiosResponse<LogInResponseModel>;

  return response.data;
}
