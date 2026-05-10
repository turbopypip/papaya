import {axiosInstance} from '@/shared/api/axios';
import {CreateThreadRequest, CreateThreadResponse} from '@/entities/thread';

export const postThread = async (
  thread: CreateThreadRequest,
): Promise<CreateThreadResponse> => {
  const response = await axiosInstance.post('/thread', thread);
  return response.data;
};
