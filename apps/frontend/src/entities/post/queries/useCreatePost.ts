import {postPost} from '@/entities/post/api/postPost';
import {CreatePostRequest} from '@/entities/post/types/postTypes';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useCreatePost = (threadId?: string) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (Post: CreatePostRequest) => postPost(Post),
    onSuccess: (_data, variables) => {
      const targetThreadId = threadId ?? variables.thread_id;

      queryClient.invalidateQueries({
        queryKey: ['posts', targetThreadId],
      });
      queryClient.invalidateQueries({
        queryKey: ['thread', targetThreadId],
      });
    },
  });

  return {
    createPost: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при отправке поста' : null)),
    success: mutation.isSuccess,
  };
};
