export type LikableType = 'post' | 'comment';

export interface LikeState {
  likable_id: string;
  likable_type: LikableType;
  count: number;
  liked_by_me: boolean;
}

export interface LikeRequest {
  likable_id: string;
  likable_type: LikableType;
}

export interface LikeMutationResponse {
  message: string;
  state: LikeState;
}
