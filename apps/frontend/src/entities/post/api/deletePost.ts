import {DeletePostResponse} from '@/entities/post/types/postTypes';
import {axiosInstance} from '@/shared/api/axios';

export async function deletePost(postId: string): Promise<DeletePostResponse> {
  const response = await axiosInstance.delete(`/post/${postId}`);
  return response.data;
}
