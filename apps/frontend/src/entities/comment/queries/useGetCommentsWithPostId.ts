import {getCommentsWithPostId} from '@/entities/comment/api/getCommentsWithPostId';
import {useQuery} from '@tanstack/react-query';

export const useGetCommentsWithPostId = (
  postId?: string,
  page = 1,
  limit = 100,
) => {
  const query = useQuery({
    queryKey: ['comments', postId, page, limit],
    queryFn: () => getCommentsWithPostId(postId ?? '', page, limit),
    enabled: Boolean(postId),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  });

  return {
    comments: query.data?.comments ?? [],
    loaded: query.isLoading,
    error:
      query.data?.error ??
      ((query.error as any)?.response?.data?.error ||
        (query.error as any)?.response?.data?.message ||
        (query.error ? 'Ошибка получения комментариев' : null)),
    fetchComments: query.refetch,
    refetch: query.refetch,
  };
};
