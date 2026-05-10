import {getThreads} from '@/entities/thread/api/getThreads';
import {useState} from 'react';
import {Thread} from '@/entities/thread/types/threadTypes';

export const useGetThreads = () => {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThreads = async (page: number, limit: number) => {
    try {
      setLoaded(true);
      setError(null);

      const response = await getThreads(page, limit);

      if (response.error) {
        setError(response.error);
      }

      setThreads(response.threads);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || 'Ошибка получения тредов';
      setError(errorMessage);
    } finally {
      setLoaded(false);
    }
  };

  return {threads, loaded, error, fetchThreads};
};
