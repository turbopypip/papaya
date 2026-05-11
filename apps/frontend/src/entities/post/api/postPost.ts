import {
  CreatePostRequest,
  CreatePostResponse,
} from '@/entities/post/types/postTypes';
import {axiosInstance} from '@/shared/api/axios';

export async function postPost(
  Post: CreatePostRequest,
): Promise<CreatePostResponse> {
  const response = await axiosInstance.post('/post', Post, {
    headers: {'Content-Type': 'application/json'},
    withCredentials: true,
  });
  return response.data;
}

export const postThread = postPost;
