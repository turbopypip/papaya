import {deleteComment} from '@/entities/comment/api/deleteComment';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useDeleteComment = (postId: string) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (commentId: string) => deleteComment(commentId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['comments', postId],
      });
    },
  });

  return {
    deleteComment: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при удалении комментария' : null)),
    success: mutation.isSuccess,
  };
};
