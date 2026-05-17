import {logInRequest} from '../api/logIn';
import {LogInRequestModel} from '@/entities/user/types/userTypes';
import {useMutation, useQueryClient} from '@tanstack/react-query';
import {completeAuthSuccess} from '@/entities/user/lib/authSuccess';
import {getApiErrorMessage} from '@/entities/user/lib/apiError';

export const useLogIn = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (data: LogInRequestModel) => {
      await logInRequest(data);
      return completeAuthSuccess(queryClient);
    },
  });

  return {
    logIn: mutation.mutateAsync,
    loaded: mutation.isPending,
    error: mutation.error
      ? getApiErrorMessage(mutation.error, 'Ошибка входа')
      : null,
  };
};
