import {useState} from 'react';
import {getPosts} from '@/entities/post/api/getPosts';
import {Post} from '@/entities/post/types/postTypes';

export const useGetPosts = (threadId: string) => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPosts = async (page: number, limit: number) => {
    try {
      setLoaded(true);
      setError(null);

      const response = await getPosts(threadId, page, limit);

      if (response.error) {
        setError(response.error);
      }

      setPosts(response.posts);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || 'Ошибка получения постов';
      setError(errorMessage);
    } finally {
      setLoaded(false);
    }
  };

  return {posts, loaded, error, fetchPosts};
};
