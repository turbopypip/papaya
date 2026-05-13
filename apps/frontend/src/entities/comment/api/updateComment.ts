import {
  UpdateCommentRequest,
  UpdateCommentResponse,
} from '@/entities/comment/types/commentTypes';
import {axiosMultipartInstance} from '@/shared/api/axios';

export async function updateComment(
  comment: UpdateCommentRequest,
): Promise<UpdateCommentResponse> {
  const formData = new FormData();
  formData.append('content', comment.content);
  formData.append('replace_attachments', 'true');
  comment.keep_attachment_ids?.forEach(id =>
    formData.append('keep_attachment_ids', id),
  );
  comment.attachments?.forEach(file => formData.append('attachments', file));

  const response = await axiosMultipartInstance.put(
    `/comment/${comment.id}`,
    formData,
  );
  return response.data;
}
