import {getPosts} from '@/entities/post/api/getPosts';
import {useInfiniteQuery} from '@tanstack/react-query';

export const useGetPosts = (threadId: string, enabled = true) => {
  const limit = 10;

  const query = useInfiniteQuery({
    queryKey: ['posts', threadId, 'infinite', limit],
    queryFn: ({pageParam}) => getPosts(threadId, pageParam, limit),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      if ((lastPage.posts ?? []).length < limit) {
        return undefined;
      }

      return allPages.length + 1;
    },
    enabled: enabled && Boolean(threadId),
    refetchInterval: enabled ? 2000 : false,
    refetchIntervalInBackground: enabled,
  });

  const posts = query.data?.pages.flatMap(page => page.posts ?? []) ?? [];

  return {
    posts,
    loaded: query.isLoading,
    loadingMore: query.isFetchingNextPage,
    hasMore: query.hasNextPage,
    error:
      query.data?.pages.find(page => page.error)?.error ??
      ((query.error as any)?.response?.data?.error ||
        (query.error as any)?.response?.data?.message ||
        (query.error ? 'Ошибка получения постов' : null)),
    loadMore: query.fetchNextPage,
    fetchPosts: query.refetch,
    refetch: query.refetch,
  };
};
