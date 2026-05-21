import {useQuery} from '@tanstack/react-query';
import {searchThreads} from '@/entities/thread/api/searchThreads';

export const useSearchThreads = (
  query: string,
  page = 1,
  limit = 10,
  enabled = true,
) => {
  const normalizedQuery = query.trim();

  const searchQuery = useQuery({
    queryKey: ['threads', 'search', normalizedQuery, page, limit],
    queryFn: () => searchThreads(normalizedQuery, page, limit),
    enabled: enabled && normalizedQuery.length > 0,
  });

  return {
    threads: searchQuery.data?.threads ?? [],
    total: searchQuery.data?.total ?? 0,
    page: searchQuery.data?.page ?? page,
    limit: searchQuery.data?.limit ?? limit,
    loaded: searchQuery.isLoading,
    error:
      searchQuery.data?.error ??
      ((searchQuery.error as any)?.response?.data?.error ||
        (searchQuery.error as any)?.response?.data?.message ||
        (searchQuery.error ? 'Ошибка поиска тредов' : null)),
    refetch: searchQuery.refetch,
  };
};
