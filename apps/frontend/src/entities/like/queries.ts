import {createLike, deleteLike, getLikeState} from './api';
import {LikableType, LikeRequest, LikeState} from './types';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';

const likeKey = (likableType: LikableType, likableId: string) => [
  'likes',
  likableType,
  likableId,
];

export const useLike = (likableType: LikableType, likableId: string) => {
  const queryClient = useQueryClient();
  const request: LikeRequest = {
    likable_id: likableId,
    likable_type: likableType,
  };

  const query = useQuery({
    queryKey: likeKey(likableType, likableId),
    queryFn: () => getLikeState(request),
    enabled: Boolean(likableId),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  });

  const mutation = useMutation({
    mutationFn: (nextLiked: boolean) =>
      nextLiked ? createLike(request) : deleteLike(request),
    onMutate: async nextLiked => {
      await queryClient.cancelQueries({
        queryKey: likeKey(likableType, likableId),
      });

      const previous = queryClient.getQueryData<LikeState>(
        likeKey(likableType, likableId),
      );
      const current = previous ?? {
        likable_id: likableId,
        likable_type: likableType,
        count: 0,
        liked_by_me: false,
      };

      queryClient.setQueryData<LikeState>(likeKey(likableType, likableId), {
        ...current,
        count: Math.max(current.count + (nextLiked ? 1 : -1), 0),
        liked_by_me: nextLiked,
      });

      return {previous, current};
    },
    onError: (_error, _nextLiked, context) => {
      queryClient.setQueryData(
        likeKey(likableType, likableId),
        context?.previous ?? context?.current,
      );
    },
    onSuccess: response => {
      queryClient.setQueryData(
        likeKey(likableType, likableId),
        response.state,
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: likeKey(likableType, likableId),
      });
    },
  });

  const state = query.data ?? {
    likable_id: likableId,
    likable_type: likableType,
    count: 0,
    liked_by_me: false,
  };

  return {
    count: state.count,
    likedByMe: state.liked_by_me,
    loaded: query.isLoading,
    loading: mutation.isPending,
    error:
      ((query.error || mutation.error) as any)?.response?.data?.message ||
      ((query.error || mutation.error) ? 'Ошибка обновления лайка' : null),
    toggleLike: () => mutation.mutateAsync(!state.liked_by_me),
  };
};

export {likeKey};
