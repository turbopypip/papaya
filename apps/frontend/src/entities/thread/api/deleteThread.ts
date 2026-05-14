import {DeleteThreadResponse} from '@/entities/thread/types/threadTypes';
import {axiosInstance} from '@/shared/api/axios';

export async function deleteThread(
  threadId: string,
): Promise<DeleteThreadResponse> {
  const response = await axiosInstance.delete(`/thread/${threadId}`);
  return response.data;
}
