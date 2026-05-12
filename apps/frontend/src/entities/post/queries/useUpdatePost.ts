import {updatePost} from '@/entities/post/api/updatePost';
import {UpdatePostRequest} from '@/entities/post/types/postTypes';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useUpdatePost = (threadId?: string) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (post: UpdatePostRequest) => updatePost(post),
    onSuccess: data => {
      const targetThreadId = threadId ?? data.post?.thread_id;
      if (!targetThreadId) {
        return;
      }

      queryClient.invalidateQueries({
        queryKey: ['posts', targetThreadId],
      });
      queryClient.invalidateQueries({
        queryKey: ['thread', targetThreadId],
      });
    },
  });

  return {
    updatePost: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при обновлении поста' : null)),
    success: mutation.isSuccess,
  };
};
