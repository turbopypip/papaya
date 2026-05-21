import {axiosInstance} from '@/shared/api/axios';
import {RecommendationEventRequest} from '@/entities/recommendation/types/recommendationTypes';

export async function recordRecommendationEvent(
  payload: RecommendationEventRequest,
): Promise<void> {
  await axiosInstance.post('/analytics/recommendations/event', payload, {
    withCredentials: true,
  });
}
