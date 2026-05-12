import {
  UpdatePostRequest,
  UpdatePostResponse,
} from '@/entities/post/types/postTypes';
import {axiosMultipartInstance} from '@/shared/api/axios';

export async function updatePost(
  post: UpdatePostRequest,
): Promise<UpdatePostResponse> {
  const formData = new FormData();
  formData.append('content', post.content);
  formData.append('replace_attachments', 'true');
  post.keep_attachment_ids?.forEach(id =>
    formData.append('keep_attachment_ids', id),
  );
  post.attachments?.forEach(file => formData.append('attachments', file));

  const response = await axiosMultipartInstance.put(`/post/${post.id}`, formData);
  return response.data;
}
