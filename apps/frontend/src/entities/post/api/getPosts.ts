import {AxiosResponse} from 'axios';
import {axiosInstance} from '@/shared/api/axios';
import {GetPostsResponse} from '@/entities/post/types/postTypes';

export async function getPosts(threadId: string, page: number, limit: number) {
  const response = (await axiosInstance.get(`/post`, {
    params: {thread_id: threadId, page, limit},
    withCredentials: true,
  })) as AxiosResponse<GetPostsResponse>;

  return response.data;
}
