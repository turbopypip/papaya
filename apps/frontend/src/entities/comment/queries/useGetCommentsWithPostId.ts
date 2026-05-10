import {getCommentsWithPostId} from '@/entities/comment/api/getCommentsWithPostId';
import {useState} from 'react';
import {Comment} from '@/entities/comment/types/commentTypes';

export const useGetCommentsWithPostId = () => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComments = async (
    post_id: string,
    page: number,
    limit: number,
  ) => {
    try {
      setLoaded(true);
      setError(null);

      const response = await getCommentsWithPostId(post_id, page, limit);

      if (response.error) {
        setError(response.error);
      }

      setComments(response.comments);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || 'Ошибка получения комментариев';
      setError(errorMessage);
    } finally {
      setLoaded(false);
    }
  };

  return {comments, loaded, error, fetchComments};
};
