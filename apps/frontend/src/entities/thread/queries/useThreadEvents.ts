import {useEffect} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import {API_URL} from '@/shared/consts';
import {LikeState, LikableType} from '@/entities/like';

type ThreadEvent = {
  type: string;
  thread_id: string;
  post_id?: string;
  comment_id?: string;
  likable_type?: LikableType;
  likable_id?: string;
  count?: number;
};

const eventsUrl = (threadId: string) => {
  const baseUrl = API_URL ? `${API_URL}/api/v1` : '/api/v1';
  return `${baseUrl}/events/thread/${threadId}`;
};

export const useThreadEvents = (threadId: string, enabled = true) => {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || !threadId || typeof window === 'undefined') {
      return;
    }

    const eventSource = new EventSource(eventsUrl(threadId), {
      withCredentials: true,
    });

    const onPostChanged = () => {
      queryClient.invalidateQueries({queryKey: ['posts', threadId]});
      queryClient.invalidateQueries({queryKey: ['thread', threadId]});
    };

    const onCommentChanged = (event: MessageEvent) => {
      const payload = parseEvent(event);
      if (payload?.post_id) {
        queryClient.invalidateQueries({
          queryKey: ['comments', payload.post_id],
        });
      }
    };

    const onLikeChanged = (event: MessageEvent) => {
      const payload = parseEvent(event);
      if (!payload?.likable_type || !payload.likable_id) {
        return;
      }

      queryClient.setQueryData<LikeState>(
        ['likes', payload.likable_type, payload.likable_id],
        current => ({
          likable_id: payload.likable_id ?? current?.likable_id ?? '',
          likable_type: payload.likable_type ?? current?.likable_type ?? 'post',
          count: payload.count ?? current?.count ?? 0,
          liked_by_me: current?.liked_by_me ?? false,
        }),
      );
    };

    eventSource.addEventListener('post.created', onPostChanged);
    eventSource.addEventListener('post.updated', onPostChanged);
    eventSource.addEventListener('post.deleted', onPostChanged);
    eventSource.addEventListener('thread.updated', onPostChanged);
    eventSource.addEventListener('thread.deleted', onPostChanged);
    eventSource.addEventListener('comment.created', onCommentChanged);
    eventSource.addEventListener('comment.updated', onCommentChanged);
    eventSource.addEventListener('comment.deleted', onCommentChanged);
    eventSource.addEventListener('like.created', onLikeChanged);
    eventSource.addEventListener('like.deleted', onLikeChanged);
    return () => {
      eventSource.removeEventListener('post.created', onPostChanged);
      eventSource.removeEventListener('post.updated', onPostChanged);
      eventSource.removeEventListener('post.deleted', onPostChanged);
      eventSource.removeEventListener('thread.updated', onPostChanged);
      eventSource.removeEventListener('thread.deleted', onPostChanged);
      eventSource.removeEventListener('comment.created', onCommentChanged);
      eventSource.removeEventListener('comment.updated', onCommentChanged);
      eventSource.removeEventListener('comment.deleted', onCommentChanged);
      eventSource.removeEventListener('like.created', onLikeChanged);
      eventSource.removeEventListener('like.deleted', onLikeChanged);
      eventSource.close();
    };
  }, [enabled, queryClient, threadId]);
};

const parseEvent = (event: MessageEvent): ThreadEvent | null => {
  try {
    return JSON.parse(event.data) as ThreadEvent;
  } catch {
    return null;
  }
};
