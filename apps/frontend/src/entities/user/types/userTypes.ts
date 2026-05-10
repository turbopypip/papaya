export interface Permissions {
  threads: {
    create: boolean;
    read: boolean;
    update: boolean;
    delete: boolean;
  };
  comments: {
    create: boolean;
    read: boolean;
    update: boolean;
    delete: boolean;
  };
  users: {
    create: boolean;
    read: boolean;
    update: boolean;
    delete: boolean;
  };
  categories: {
    create: boolean;
    read: boolean;
    update: boolean;
    delete: boolean;
  };
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
  roleId: string; // UUID as string
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
