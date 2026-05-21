import {axiosInstance} from '@/shared/api/axios';
import {AxiosResponse} from 'axios';
import {GetThreadRecommendationsResponse} from '@/entities/recommendation/types/recommendationTypes';

export async function getThreadRecommendations(
  limit = 10,
): Promise<GetThreadRecommendationsResponse> {
  const response = (await axiosInstance.get('/recommendations/threads', {
    params: {limit},
    withCredentials: true,
  })) as AxiosResponse<GetThreadRecommendationsResponse>;

  return response.data;
}
