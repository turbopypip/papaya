import {deletePost} from '@/entities/post/api/deletePost';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useDeletePost = (threadId: string) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (postId: string) => deletePost(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['posts', threadId],
      });
      queryClient.invalidateQueries({
        queryKey: ['thread', threadId],
      });
    },
  });

  return {
    deletePost: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при удалении поста' : null)),
    success: mutation.isSuccess,
  };
};
