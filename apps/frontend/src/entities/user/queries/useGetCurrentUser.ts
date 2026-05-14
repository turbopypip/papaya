import {getCurrentUser} from '@/entities/user/api/getCurrentUser';
import {useQuery} from '@tanstack/react-query';

export const useGetCurrentUser = (enabled = true) => {
  const query = useQuery({
    queryKey: ['current-user'],
    queryFn: getCurrentUser,
    enabled,
  });

  return {
    user: query.data?.user ?? null,
    loaded: query.isLoading,
    error:
      query.data?.error ??
      ((query.error as any)?.response?.data?.error ||
        (query.error as any)?.response?.data?.message ||
        (query.error ? 'Ошибка получения пользователя' : null)),
    refetch: query.refetch,
  };
};
