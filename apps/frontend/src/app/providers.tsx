'use client';

import React, {useEffect, useState} from 'react';
import {ChakraProvider, defaultSystem} from '@chakra-ui/react';
import {
  QueryClient,
  QueryClientProvider,
  useQueryClient,
} from '@tanstack/react-query';
import {AUTH_CHANGED_EVENT} from '@/entities/user/lib/authEvents';

const AuthQueryBoundary = ({children}: {children: React.ReactNode}) => {
  const queryClient = useQueryClient();

  useEffect(() => {
    const resetUserScopedCache = () => {
      queryClient.clear();
    };

    window.addEventListener(AUTH_CHANGED_EVENT, resetUserScopedCache);

    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, resetUserScopedCache);
    };
  }, [queryClient]);

  return children;
};

const Providers = ({children}: {children: React.ReactNode}) => {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthQueryBoundary>
        <ChakraProvider value={defaultSystem}>{children}</ChakraProvider>
      </AuthQueryBoundary>
    </QueryClientProvider>
  );
};

export default Providers;
