'use client';

import React, {FC} from 'react';
import {Tag} from '@/shared/Components/Tag/ui/tag';
import {useRouter} from 'next/navigation';
import {Box, Table, Text} from '@chakra-ui/react';
import {Thread} from '@/entities/thread';
import {StatePanel} from '@/shared/Components/StatePanel';

type Props = {
  threads: Thread[];
  loaded: boolean;
  error: string | null;
  emptyTitle?: string;
  emptyMessage?: string;
};
const ThreadsTable: FC<Props> = ({
  threads,
  loaded,
  error,
  emptyTitle = 'Пока нет тредов',
  emptyMessage = 'Начните первое обсуждение, когда будете готовы.',
}) => {
  const router = useRouter();
  if (loaded) {
    return (
      <StatePanel title="Загружаем треды">
        Свежие обсуждения уже в пути.
      </StatePanel>
    );
  }

  if (error) {
    return (
      <StatePanel title="Не удалось загрузить треды" tone="danger">
        {error}
      </StatePanel>
    );
  }
  const handleClick = (threadId: string) => {
    router.push(`/thread/${threadId}`);
  };

  if (threads.length == 0) {
    return (
      <StatePanel title={emptyTitle}>{emptyMessage}</StatePanel>
    );
  }

  return (
    <Box overflowX="auto" width="100%">
      <Box
        borderWidth="1px"
        borderColor="gray.200"
        borderRadius="8px"
        overflow="hidden">
        <Table.Root interactive variant="line" width="100%">
          <Table.Header>
            <Table.Row bg="gray.100">
              <Table.ColumnHeader
                bg="gray.100"
                color="gray.600"
                fontWeight="600">
                Заголовок
              </Table.ColumnHeader>
              <Table.ColumnHeader
                bg="gray.100"
                color="gray.600"
                fontWeight="600">
                Автор
              </Table.ColumnHeader>
              <Table.ColumnHeader
                bg="gray.100"
                color="gray.600"
                fontWeight="600"
                textAlign="end">
                Категории
              </Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {threads?.map((thread, index) => (
              <Table.Row
                cursor="pointer"
                onClick={() => handleClick(thread.ID)}
                key={thread.ID}>
                <Table.Cell
                  borderBottomWidth={
                    index === threads.length - 1 ? '0' : undefined
                  }
                  whiteSpace="pre-wrap"
                  overflowWrap="anywhere">
                  {thread.title}
                </Table.Cell>
                <Table.Cell
                  borderBottomWidth={
                    index === threads.length - 1 ? '0' : undefined
                  }
                  minWidth="8rem">
                  <Text color="gray.600" fontSize="sm">
                    @{thread.author?.username ?? 'неизвестно'}
                  </Text>
                </Table.Cell>
                <Table.Cell
                  borderBottomWidth={
                    index === threads.length - 1 ? '0' : undefined
                  }>
                  <Box
                    gap="2"
                    display="flex"
                    flexWrap="wrap"
                    justifyContent="flex-end">
                    {(thread.categories ?? []).map(categorie => (
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
      </Box>
    </Box>
  );
};

export default ThreadsTable;
