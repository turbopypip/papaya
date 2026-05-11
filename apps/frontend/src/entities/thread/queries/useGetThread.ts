import {getThread} from '@/entities/thread/api/getThread';
import {useQuery} from '@tanstack/react-query';

export const useGetThread = (threadId: string) => {
  const query = useQuery({
    queryKey: ['thread', threadId],
    queryFn: () => getThread(threadId),
    enabled: Boolean(threadId),
  });

  return {
    thread: query.data?.thread ?? null,
    loaded: query.isLoading,
    error:
      query.data?.error ??
      ((query.error as any)?.response?.data?.error ||
        (query.error as any)?.response?.data?.message ||
        (query.error ? 'Ошибка получения треда' : null)),
    refetch: query.refetch,
  };
};
