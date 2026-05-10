export interface Post {
  ID: string;
  content: string;
  CreatedAt: string;
}

export interface GetPostsResponse {
  error?: string;
  posts: Post[];
}

export interface CreatePostRequest {
  content: string;
  thread_id: string;
}

export interface CreatePostResponse {
  error?: string;
}
