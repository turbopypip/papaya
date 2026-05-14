import {deleteThread} from '@/entities/thread/api/deleteThread';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useDeleteThread = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (threadId: string) => deleteThread(threadId),
    onSuccess: data => {
      queryClient.invalidateQueries({queryKey: ['threads']});
      if (data.thread_id) {
        queryClient.invalidateQueries({queryKey: ['thread', data.thread_id]});
      }
    },
  });

  return {
    deleteThread: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при удалении треда' : null)),
    success: mutation.isSuccess,
  };
};
