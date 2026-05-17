import {Attachment} from '@/entities/attachment';
import {PublicUser} from '@/entities/user/types/userTypes';

export interface Post {
  ID: string;
  content: string;
  user_id: string;
  author?: PublicUser;
  thread_id: string;
  CreatedAt: string;
  UpdatedAt: string;
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

export interface UpdatePostRequest {
  id: string;
  content: string;
  keep_attachment_ids?: string[];
  attachments?: File[];
}

export interface UpdatePostResponse {
  error?: string;
  post?: Post;
}

export interface DeletePostResponse {
  error?: string;
  post_id?: string;
}
