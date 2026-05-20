import {Thread} from '@/entities/thread';

export type RecommendationStatus =
  | 'ready'
  | 'model_not_ready'
  | 'no_recommendations';

export type RecommendationEventType =
  | 'recommendation_impression'
  | 'recommendation_clicked';

export interface ThreadRecommendation {
  thread: Thread;
  score: number;
  recommendation_source: string;
  model_version: string;
  generated_at: string;
  run_id?: string;
  generation_id: string;
  metadata?: Record<string, unknown>;
}

export interface GetThreadRecommendationsResponse {
  error?: string;
  status: RecommendationStatus;
  recommendations: ThreadRecommendation[];
  model_version?: string;
  generated_at?: string;
  run_id?: string;
  generation_id?: string;
  metadata?: Record<string, unknown>;
}

export interface RecommendationEventRequest {
  event_type: RecommendationEventType;
  thread_id: string;
  model_version: string;
  position: number;
  recommendation_source: string;
  placement: string;
  run_id?: string;
  generation_id?: string;
}
