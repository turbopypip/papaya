import {axiosInstance} from '@/shared/api/axios';
import {LikeMutationResponse, LikeRequest, LikeState} from './types';

export async function getLikeState(request: LikeRequest): Promise<LikeState> {
  const response = await axiosInstance.get('/like', {
    params: {
      likable_id: request.likable_id,
      likable_type: request.likable_type,
    },
    withCredentials: true,
  });

  return response.data;
}

export async function createLike(
  request: LikeRequest,
): Promise<LikeMutationResponse> {
  const response = await axiosInstance.post('/like', request, {
    withCredentials: true,
  });

  return response.data;
}

export async function deleteLike(
  request: LikeRequest,
): Promise<LikeMutationResponse> {
  const response = await axiosInstance.delete('/like', {
    data: request,
    withCredentials: true,
  });

  return response.data;
}
