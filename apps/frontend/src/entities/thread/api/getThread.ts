import {GetThreadResponse} from '@/entities/thread/types/threadTypes';
import {AxiosResponse} from 'axios';
import {axiosInstance} from '@/shared/api/axios';

export async function getThread(threadId: string): Promise<GetThreadResponse> {
  const response = (await axiosInstance.get(`/thread/${threadId}`, {
    withCredentials: true,
  })) as AxiosResponse<GetThreadResponse>;

  return response.data;
}
