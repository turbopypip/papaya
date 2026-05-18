import React, {ReactNode} from 'react';
import {Box, Text} from '@chakra-ui/react';

type StatePanelProps = {
  title: string;
  children?: ReactNode;
  tone?: 'neutral' | 'danger';
};

export const StatePanel = ({
  title,
  children,
  tone = 'neutral',
}: StatePanelProps) => {
  const isDanger = tone === 'danger';

  return (
    <Box
      role={isDanger ? 'alert' : 'status'}
      borderWidth="1px"
      borderColor={isDanger ? 'red.200' : 'gray.200'}
      bg={isDanger ? 'red.50' : 'gray.50'}
      borderRadius="8px"
      padding={{base: '1rem', md: '1.25rem'}}
      marginTop="0.5rem"
      overflowWrap="anywhere">
      <Text fontWeight="600" color={isDanger ? 'red.700' : 'gray.700'}>
        {title}
      </Text>
      {children ? (
        <Text marginTop="0.35rem" color={isDanger ? 'red.600' : 'gray.600'}>
          {children}
        </Text>
      ) : null}
    </Box>
  );
};
