import {getPosts} from '@/entities/post/api/getPosts';
import {useQuery} from '@tanstack/react-query';

export const useGetPosts = (threadId: string, enabled = true) => {
  const page = 1;
  const limit = 100;

  const query = useQuery({
    queryKey: ['posts', threadId, page, limit],
    queryFn: () => getPosts(threadId, page, limit),
    enabled: enabled && Boolean(threadId),
    refetchInterval: enabled ? 2000 : false,
    refetchIntervalInBackground: enabled,
  });

  return {
    posts: query.data?.posts ?? [],
    loaded: query.isLoading,
    error:
      query.data?.error ??
      ((query.error as any)?.response?.data?.message ||
        (query.error ? 'Ошибка получения постов' : null)),
    fetchPosts: query.refetch,
    refetch: query.refetch,
  };
};
