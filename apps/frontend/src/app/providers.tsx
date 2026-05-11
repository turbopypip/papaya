'use client';

import React, {useState} from 'react';
import {ChakraProvider, defaultSystem} from '@chakra-ui/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';

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
      <ChakraProvider value={defaultSystem}>{children}</ChakraProvider>
    </QueryClientProvider>
  );
};

export default Providers;
