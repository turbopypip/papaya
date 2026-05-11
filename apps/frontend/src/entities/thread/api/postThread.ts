import {axiosInstance, axiosMultipartInstance} from '@/shared/api/axios';
import {CreateThreadRequest, CreateThreadResponse} from '@/entities/thread';

export const postThread = async (
  thread: CreateThreadRequest,
): Promise<CreateThreadResponse> => {
  if (thread.attachments?.length) {
    const formData = new FormData();
    formData.append('title', thread.title);
    thread.categories.forEach(category => formData.append('categories', category));
    thread.attachments.forEach(file => formData.append('attachments', file));

    const response = await axiosMultipartInstance.post('/thread', formData);
    return response.data;
  }

  const response = await axiosInstance.post('/thread', thread);
  return response.data;
};
