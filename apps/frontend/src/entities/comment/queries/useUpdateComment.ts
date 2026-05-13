import {updateComment} from '@/entities/comment/api/updateComment';
import {UpdateCommentRequest} from '@/entities/comment/types/commentTypes';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export const useUpdateComment = (postId?: string) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (comment: UpdateCommentRequest) => updateComment(comment),
    onSuccess: data => {
      const targetPostId = postId ?? data.comment?.post_id;
      if (!targetPostId) {
        return;
      }

      queryClient.invalidateQueries({
        queryKey: ['comments', targetPostId],
      });
    },
  });

  return {
    updateComment: mutation.mutateAsync,
    loading: mutation.isPending,
    error:
      mutation.data?.error ??
      ((mutation.error as any)?.response?.data?.error ||
        (mutation.error as any)?.response?.data?.message ||
        (mutation.error ? 'Ошибка при обновлении комментария' : null)),
    success: mutation.isSuccess,
  };
};
