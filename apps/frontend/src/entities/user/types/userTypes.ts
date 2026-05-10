export interface Permissions {
  threads: ResourcePermissions;
  posts: ResourcePermissions;
  comments: ResourcePermissions;
  categories: ResourcePermissions;
  likes: ResourcePermissions;
  attachments: ResourcePermissions;
  users: UserPermissions;
}

export interface ResourcePermissions {
  create: boolean;
  read: boolean;
  update_own: boolean;
  update_any: boolean;
  delete_own: boolean;
  delete_any: boolean;
}

export interface UserPermissions extends ResourcePermissions {
  ban: boolean;
}

export interface Role {
  id: string; // UUID as string
  name: string;
  permissions: Permissions;
  createdAt: string; // ISO string for date
  updatedAt: string; // ISO string for date
}

export interface User {
  id: string; // UUID as string
  username: string;
  email: string;
  passwordHash: string;
  roleId: string; // UUID as string
  createdAt: string; // ISO string for date
  updatedAt: string; // ISO string for date
}

export interface SignUpRequestModel {
  username: string;
  email: string;
  password: string;
}

export interface SignUpResponseModel {
  message: string;
  user: User;
}
export interface LogInRequestModel {
  email: string;
  password: string;
}

export interface LogInResponseModel {
  description?: string;
  error?: string;
}
