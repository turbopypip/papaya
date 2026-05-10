import {postComment} from '@/entities/comment/api/postComment';
import {useState} from 'react';
import {CreateCommentRequest} from '@/entities/comment/types/commentTypes';
import {postThread} from '@/entities/post/api/postPost';

export const useCreateComment = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean | null>(null);

  const createComment = async (comment: CreateCommentRequest) => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await postComment(comment);

      if (response.error) {
        setError(response.error);
      } else {
        setSuccess(true);
      }
    } catch (err) {
      setError('Ошибка при отправке поста');
    } finally {
      setLoading(false);
    }
  };

  return {createComment, loading, error, success};
};
