import {QueryClient} from '@tanstack/react-query';
import {getCurrentUser} from '@/entities/user/api/getCurrentUser';
import {useUserStore} from '@/entities/user/stores/userStore';
import {
  emitAuthChanged,
  enableDevAutoLogin,
} from '@/entities/user/lib/authEvents';
import {User} from '@/entities/user/types/userTypes';

export async function completeAuthSuccess(
  queryClient: QueryClient,
): Promise<User> {
  enableDevAutoLogin();
  emitAuthChanged();

  const currentUserResponse = await getCurrentUser();
  if (!currentUserResponse.user) {
    throw new Error('Failed to load current user');
  }

  queryClient.setQueryData(['current-user'], currentUserResponse);
  useUserStore.getState().setUser(currentUserResponse.user);

  return currentUserResponse.user;
}
