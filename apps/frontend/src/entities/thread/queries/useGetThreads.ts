import {getThreads} from '@/entities/thread/api/getThreads';
import {useQuery} from '@tanstack/react-query';

export const useGetThreads = (page = 1, limit = 100, enabled = true) => {
  const query = useQuery({
    queryKey: ['threads', page, limit],
    queryFn: () => getThreads(page, limit),
    enabled,
    refetchInterval: enabled ? 3000 : false,
    refetchIntervalInBackground: enabled,
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
