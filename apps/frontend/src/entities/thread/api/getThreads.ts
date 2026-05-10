import {GetThreadsResponse} from '@/entities/thread/types/threadTypes';
import {AxiosResponse} from 'axios';
import {axiosInstance} from '@/shared/api/axios';

export async function getThreads(
  page: number,
  limit: number,
): Promise<GetThreadsResponse> {
  const response = (await axiosInstance.get(`/thread/all`, {
    params: {page, limit},
    withCredentials: true,
  })) as AxiosResponse<GetThreadsResponse>;

  return response.data;
}
