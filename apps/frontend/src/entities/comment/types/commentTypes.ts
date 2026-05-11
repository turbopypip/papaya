import {Attachment} from '@/entities/attachment';

export interface Comment {
  ID: string;
  content: string;
  post_id: string;
  CreatedAt: string;
  attachments?: Attachment[];
  // likes
}

export interface CreateCommentRequest {
  content: string;
  post_id: string;
  attachments?: File[];
}

export interface CreateCommentResponse {
  error?: string;
  details?: string;
  comment?: Comment;
}

export interface GetCommentsResponseWithPostIdResponse {
  error?: string;
  comments: Comment[];
}
