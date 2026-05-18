import {GetThreadsResponse} from '@/entities/thread/types/threadTypes';
import {axiosInstance} from '@/shared/api/axios';
import {AxiosResponse} from 'axios';

export async function searchThreads(
  query: string,
  page: number,
  limit: number,
): Promise<GetThreadsResponse> {
  const response = (await axiosInstance.get('/thread/search', {
    params: {title: query, page, limit},
    withCredentials: true,
  })) as AxiosResponse<GetThreadsResponse>;

  return response.data;
}
