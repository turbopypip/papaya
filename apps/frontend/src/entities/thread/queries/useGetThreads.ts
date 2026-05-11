import {getThreads} from '@/entities/thread/api/getThreads';
import {useQuery} from '@tanstack/react-query';

export const useGetThreads = (page = 1, limit = 100) => {
  const query = useQuery({
    queryKey: ['threads', page, limit],
    queryFn: () => getThreads(page, limit),
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  return {
    threads: query.data?.threads ?? [],
    loaded: query.isLoading,
    error:
      query.data?.error ??
      ((query.error as any)?.response?.data?.message ||
        (query.error ? 'Ошибка получения тредов' : null)),
    fetchThreads: query.refetch,
    refetch: query.refetch,
  };
};
