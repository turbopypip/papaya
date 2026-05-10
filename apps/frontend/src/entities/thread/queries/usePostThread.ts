import {useState} from 'react';
import {postThread} from '@/entities/thread/api/postThread';
import {CreateThreadRequest} from '@/entities/thread/types/threadTypes';

export const usePostThread = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean | null>(null);

  const createThread = async (thread: CreateThreadRequest) => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await postThread(thread);

      if (response.error) {
        setError(response.error);
      } else {
        setSuccess(true);
      }
    } catch (err) {
      setError('Ошибка при отправке треда');
    } finally {
      setLoading(false);
    }
  };

  return {createThread, loading, error, success};
};
