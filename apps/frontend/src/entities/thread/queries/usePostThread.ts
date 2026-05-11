import {postThread} from '@/entities/thread/api/postThread';
import {CreateThreadRequest} from '@/entities/thread/types/threadTypes';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const usePostThread = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (thread: CreateThreadRequest) => postThread(thread),
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['threads']});
    },
  });

  return {
    createThread: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      (mutation.data?.error as string | undefined) ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при отправке треда' : null)),
    success: mutation.isSuccess,
  };
};
