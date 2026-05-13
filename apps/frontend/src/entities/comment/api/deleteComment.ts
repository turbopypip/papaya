import {DeleteCommentResponse} from '@/entities/comment/types/commentTypes';
import {axiosInstance} from '@/shared/api/axios';

export async function deleteComment(
  commentId: string,
): Promise<DeleteCommentResponse> {
  const response = await axiosInstance.delete(`/comment/${commentId}`);
  return response.data;
}
