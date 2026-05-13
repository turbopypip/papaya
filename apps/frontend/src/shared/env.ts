export const APP_MODE = process.env.NEXT_PUBLIC_APP_MODE ?? 'prod';
export const IS_DEV_MODE = APP_MODE === 'dev';
