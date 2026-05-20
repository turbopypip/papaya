import {getThreadRecommendations} from '@/entities/recommendation/api/getThreadRecommendations';
import {useQuery} from '@tanstack/react-query';

export const useThreadRecommendations = (
  limit = 10,
  enabled = true,
) => {
  const query = useQuery({
    queryKey: ['threadRecommendations', limit],
    queryFn: () => getThreadRecommendations(limit),
    enabled,
    refetchInterval: enabled ? 30000 : false,
    refetchIntervalInBackground: false,
  });

  return {
    recommendations: query.data?.recommendations ?? [],
    status: query.data?.status ?? 'model_not_ready',
    modelVersion: query.data?.model_version ?? null,
    generatedAt: query.data?.generated_at ?? null,
    runId: query.data?.run_id ?? null,
    loaded: query.isLoading,
    error:
      query.data?.error ??
      ((query.error as any)?.response?.data?.error ||
        (query.error as any)?.response?.data?.message ||
        (query.error ? 'Ошибка получения рекомендаций' : null)),
    refetch: query.refetch,
  };
};
