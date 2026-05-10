export interface Comment {
  ID: string;
  content: string;
  post_id: string;
  CreatedAt: string;
  // likes
}

export interface CreateCommentRequest {
  content: string;
  post_id: string;
}

export interface CreateCommentResponse {
  error?: string;
  details?: string;
}

export interface GetCommentsResponseWithPostIdResponse {
  error?: string;
  comments: Comment[];
}
