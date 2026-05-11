import {postComment} from '@/entities/comment/api/postComment';
import {CreateCommentRequest} from '@/entities/comment/types/commentTypes';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useCreateComment = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (comment: CreateCommentRequest) => postComment(comment),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({queryKey: ['comments', variables.post_id]});
    },
  });

  return {
    createComment: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при отправке комментария' : null)),
    success: mutation.isSuccess,
  };
};
