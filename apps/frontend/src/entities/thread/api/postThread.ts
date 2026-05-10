import axios from 'axios';
import {CreateThreadRequest, CreateThreadResponse} from '@/entities/thread';

export const postThread = async (
  thread: CreateThreadRequest,
): Promise<CreateThreadResponse> => {
  const response = await axios.post(
    'http://localhost:8888/api/v1/thread',
    thread,
    {
      headers: {'Content-Type': 'application/json'},
      withCredentials: true,
    },
  );
  return response.data;
};
