import {Attachment} from '@/entities/attachment';

export interface Post {
  ID: string;
  content: string;
  thread_id: string;
  CreatedAt: string;
  attachments?: Attachment[];
}

export interface GetPostsResponse {
  error?: string;
  posts: Post[];
}

export interface CreatePostRequest {
  content: string;
  thread_id: string;
  attachments?: File[];
}

export interface CreatePostResponse {
  error?: string;
  post?: Post;
}
