import {useState} from 'react';
import {postThread} from '@/entities/post/api/postPost';
import {CreatePostRequest} from '@/entities/post/types/postTypes';

export const useCreatePost = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean | null>(null);

  const createPost = async (Post: CreatePostRequest) => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await postThread(Post);

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

  return {createPost, loading, error, success};
};
