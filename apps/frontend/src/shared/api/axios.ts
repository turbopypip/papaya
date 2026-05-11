import axios from 'axios';
import {API_URL} from '../consts';

export const axiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

axiosInstance.interceptors.response.use(
  response => response,
  error => {
    console.error(error.response?.data?.message || 'Ошибка сервера');
    return Promise.reject(error);
  },
);

export const axiosMultipartInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  withCredentials: true,
});

axiosMultipartInstance.interceptors.response.use(
  response => response,
  error => {
    console.error(error.response?.data?.message || 'Ошибка сервера');
    return Promise.reject(error);
  },
);

export const axiosInstanceAdmin = axios.create({
  baseURL: `${API_URL}/api/v1/admin`,
  withCredentials: true, // Включаем отправку cookie
});
