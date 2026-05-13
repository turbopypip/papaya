import {Attachment} from '@/entities/attachment';

export interface Comment {
  ID: string;
  content: string;
  user_id: string;
  post_id: string;
  CreatedAt: string;
  UpdatedAt: string;
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

export interface UpdateCommentRequest {
  id: string;
  content: string;
  post_id?: string;
  keep_attachment_ids?: string[];
  attachments?: File[];
}

export interface UpdateCommentResponse {
  error?: string;
  comment?: Comment;
}

export interface DeleteCommentResponse {
  error?: string;
  comment_id?: string;
}

export interface GetCommentsResponseWithPostIdResponse {
  error?: string;
  comments: Comment[];
}
