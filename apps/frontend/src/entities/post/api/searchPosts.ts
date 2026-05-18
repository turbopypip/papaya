import {AxiosResponse} from 'axios';
import {axiosInstance} from '@/shared/api/axios';
import {GetPostsResponse} from '@/entities/post/types/postTypes';

export async function searchPosts(
  threadId: string,
  query: string,
  page = 1,
  limit = 100,
): Promise<GetPostsResponse> {
  const response = (await axiosInstance.get('/post/search', {
    params: {thread_id: threadId, query, page, limit},
    withCredentials: true,
  })) as AxiosResponse<GetPostsResponse>;

  return response.data;
}
