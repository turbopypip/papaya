import {
  CreatePostRequest,
  CreatePostResponse,
} from '@/entities/post/types/postTypes';
import {axiosInstance, axiosMultipartInstance} from '@/shared/api/axios';

export async function postPost(
  Post: CreatePostRequest,
): Promise<CreatePostResponse> {
  if (Post.attachments?.length) {
    const formData = new FormData();
    formData.append('content', Post.content);
    formData.append('thread_id', Post.thread_id);
    Post.attachments.forEach(file => formData.append('attachments', file));

    const response = await axiosMultipartInstance.post('/post', formData);
    return response.data;
  }

  const response = await axiosInstance.post('/post', Post, {
    headers: {'Content-Type': 'application/json'},
    withCredentials: true,
  });
  return response.data;
}

export const postThread = postPost;
