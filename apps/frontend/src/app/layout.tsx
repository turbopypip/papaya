'use client';

import '@/shared/styles/globals.css';
import {Box} from '@chakra-ui/react';
import Navbar from '@/widgets/Navbar/ui/Navbar';
import Footer from '@/widgets/Footer/ui/Footer';
import Providers from '@/app/providers';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>
        <Providers>
          <Box style={{minHeight: 'calc(100vh - 60px)'}}>
            <Navbar />
            <Box overflow="auto">{children}</Box>
          </Box>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
