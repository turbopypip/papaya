import {axiosInstance} from '@/shared/api/axios';

export async function recordThreadView(threadId: string): Promise<void> {
  await axiosInstance.post(`/analytics/thread/${threadId}/view`, null, {
    withCredentials: true,
  });
}
