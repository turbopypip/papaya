import {GetCommentsResponseWithPostIdResponse} from '@/entities/comment/types/commentTypes';
import {AxiosResponse} from 'axios';
import {axiosInstance} from '@/shared/api/axios';

export async function getCommentsWithPostId(
  post_id: string,
  page: number,
  limit: number,
): Promise<GetCommentsResponseWithPostIdResponse> {
  const response = (await axiosInstance.get(`/comment`, {
    params: {post_id: post_id, page, limit},
    withCredentials: true,
  })) as AxiosResponse<GetCommentsResponseWithPostIdResponse>;
  return response.data;
}
