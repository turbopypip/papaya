import {
  CreateCommentRequest,
  CreateCommentResponse,
} from '@/entities/comment/types/commentTypes';
import {AxiosResponse} from 'axios';
import {axiosInstance, axiosMultipartInstance} from '@/shared/api/axios';

export async function postComment(
  comment: CreateCommentRequest,
): Promise<CreateCommentResponse> {
  if (comment.attachments?.length) {
    const formData = new FormData();
    formData.append('content', comment.content);
    formData.append('post_id', comment.post_id);
    comment.attachments.forEach(file => formData.append('attachments', file));

    const response = await axiosMultipartInstance.post('/comment', formData);
    return response.data;
  }

  const response = (await axiosInstance.post(`/comment`, comment, {
    withCredentials: true,
  })) as AxiosResponse<CreateCommentResponse>;
  return response.data;
}
