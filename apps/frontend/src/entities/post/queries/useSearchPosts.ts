import {searchPosts} from '@/entities/post/api/searchPosts';
import {useQuery} from '@tanstack/react-query';

export const useSearchPosts = (
  threadId: string,
  query: string,
  enabled = true,
) => {
  const normalizedQuery = query.trim();
  const page = 1;
  const limit = 100;

  const searchQuery = useQuery({
    queryKey: ['posts', threadId, 'search', normalizedQuery, page, limit],
    queryFn: () => searchPosts(threadId, normalizedQuery, page, limit),
    enabled: enabled && Boolean(threadId) && normalizedQuery.length > 0,
  });

  return {
    posts: searchQuery.data?.posts ?? [],
    loaded: searchQuery.isLoading,
    error:
      searchQuery.data?.error ??
      ((searchQuery.error as any)?.response?.data?.error ||
        (searchQuery.error as any)?.response?.data?.message ||
        (searchQuery.error ? 'Ошибка поиска постов' : null)),
    refetch: searchQuery.refetch,
  };
};
