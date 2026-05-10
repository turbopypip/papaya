import {
  CreateCommentRequest,
  CreateCommentResponse,
} from '@/entities/comment/types/commentTypes';
import {AxiosResponse} from 'axios';
import {axiosInstance} from '@/shared/api/axios';

export async function postComment(
  comment: CreateCommentRequest,
): Promise<CreateCommentResponse> {
  const response = (await axiosInstance.post(`/comment`, comment, {
    withCredentials: true,
  })) as AxiosResponse<CreateCommentResponse>;
  return response.data;
}
