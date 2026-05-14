import {
  UpdateThreadRequest,
  UpdateThreadResponse,
} from '@/entities/thread/types/threadTypes';
import {axiosMultipartInstance} from '@/shared/api/axios';

export async function updateThread(
  thread: UpdateThreadRequest,
): Promise<UpdateThreadResponse> {
  const formData = new FormData();
  formData.append('title', thread.title);
  formData.append('replace_attachments', 'true');
  thread.categories.forEach(category => formData.append('categories', category));
  thread.keep_attachment_ids?.forEach(id =>
    formData.append('keep_attachment_ids', id),
  );
  thread.attachments?.forEach(file => formData.append('attachments', file));

  const response = await axiosMultipartInstance.put(
    `/thread/${thread.id}`,
    formData,
  );
  return response.data;
}
