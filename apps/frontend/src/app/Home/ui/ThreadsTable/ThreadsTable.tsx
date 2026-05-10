'use client';

import React, {FC} from 'react';
import {Tag} from '@/shared/Components/Tag/ui/tag';
import {useRouter} from 'next/navigation';
import {Box, Table} from '@chakra-ui/react';
import {Thread} from '@/entities/thread';

type Props = {
  threads: Thread[];
  loaded: boolean;
  error: string | null;
  setThreads: (threads: Thread[]) => void;
};
const ThreadsTable: FC<Props> = ({threads, loaded, error, setThreads}) => {
  const router = useRouter();
  if (loaded) {
    return <p>Loading...</p>;
  }

  if (error) {
    return <p style={{color: 'red'}}>{error}</p>;
  }
  const handleClick = (threadId: string) => {
    router.push(`/thread/${threadId}`);
    setThreads(threads);
  };

  if (threads.length == 0) {
    return <></>;
  }

  return (
    <Table.Root
      interactive
      borderRadius="20px"
      padding="10px"
      variant="outline">
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeader>Title</Table.ColumnHeader>
          <Table.ColumnHeader textAlign="end">Categories</Table.ColumnHeader>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {threads?.map(thread => (
          <Table.Row onClick={() => handleClick(thread.ID)} key={thread.ID}>
            <Table.Cell>{thread.title}</Table.Cell>
            <Table.Cell>
              <Box gap="2" display="flex" justifyContent="flex-end">
                {thread.categories.map(categorie => (
                  <Tag key={categorie} colorScheme="purple">
                    {categorie}
                  </Tag>
                ))}
              </Box>
            </Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
};

export default ThreadsTable;
