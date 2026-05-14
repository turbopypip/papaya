import {updateThread} from '@/entities/thread/api/updateThread';
import {UpdateThreadRequest} from '@/entities/thread/types/threadTypes';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useUpdateThread = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (thread: UpdateThreadRequest) => updateThread(thread),
    onSuccess: data => {
      queryClient.invalidateQueries({queryKey: ['threads']});
      if (data.thread?.ID) {
        queryClient.invalidateQueries({queryKey: ['thread', data.thread.ID]});
      }
    },
  });

  return {
    updateThread: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при обновлении треда' : null)),
    success: mutation.isSuccess,
  };
};
