import React, {useDeferredValue, useState} from 'react';
import styles from './styles.module.css';
import {
  Link,
  Textarea,
  Tabs,
  Button,
  Input,
  Tag,
  Flex,
  Box,
  Text,
  HStack,
} from '@chakra-ui/react';
import ThreadsTable from '@/app/Home/ui/ThreadsTable/ThreadsTable';
import {useValidate} from '@/entities/user/queries/useValidate';
import {RxCross2} from 'react-icons/rx';
import {CreateThreadRequest} from '@/entities/thread';
import {usePostThread} from '@/entities/thread/queries/usePostThread';
import {AttachmentPicker} from '@/entities/attachment';
import {FaPlus} from 'react-icons/fa';
import {
  DrawerActionTrigger,
  DrawerBackdrop,
  DrawerBody,
  DrawerCloseTrigger,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerRoot,
  DrawerTitle,
  DrawerTrigger,
} from '@/shared/Components/Drawer/ui/drawer';
import {useGetThreads} from '@/entities/thread/queries/useGetThreads';
import {useSearchThreads} from '@/entities/thread/queries/useSearchThreads';
import {Search} from 'lucide-react';

const NavigationTabs = () => {
  const isAuthenticated = useValidate();
  const canFetchThreads = isAuthenticated === true;
  const [threadSearch, setThreadSearch] = useState('');
  const deferredThreadSearch = useDeferredValue(threadSearch);
  const normalizedThreadSearch = deferredThreadSearch.trim();
  const [threadPage, setThreadPage] = useState(1);
  const threadLimit = 10;
  const [threadForm, setThreadForm] = useState<CreateThreadRequest>({
    title: '',
    categories: [],
  });
  const [threadFiles, setThreadFiles] = useState<File[]>([]);
  const [threadDrawerOpen, setThreadDrawerOpen] = useState(false);

  const {threads, total, loaded, error} = useGetThreads(
    threadPage,
    threadLimit,
    canFetchThreads,
  );
  const {
    threads: foundThreads,
    total: foundThreadsTotal,
    loaded: searchLoaded,
    error: searchError,
  } = useSearchThreads(
    deferredThreadSearch,
    threadPage,
    threadLimit,
    canFetchThreads,
  );
  const {
    createThread,
    loading: creatingThread,
    error: createThreadError,
  } = usePostThread();
  const visibleThreads = normalizedThreadSearch ? foundThreads : threads;
  const visibleThreadsTotal = normalizedThreadSearch ? foundThreadsTotal : total;
  const threadsLoaded = normalizedThreadSearch ? searchLoaded : loaded;
  const threadsError = normalizedThreadSearch ? searchError : error;
  const threadPageCount = Math.max(
    1,
    Math.ceil(visibleThreadsTotal / threadLimit),
  );
  const isFirstThreadPage = threadPage <= 1;
  const isLastThreadPage = threadPage >= threadPageCount;

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const {name, value} = e.target;
    setThreadForm(prev => ({...prev, [name]: value}));
  };

  const handleCategoryKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const input = e.currentTarget.value.trim();
      if (input && !threadForm.categories.includes(input)) {
        setThreadForm(prev => ({
          ...prev,
          categories: [...prev.categories, input],
        }));
      }
      e.currentTarget.value = '';
    }
  };

  const handleDeleteCategorie = (categorie: string) => {
    setThreadForm(prev => ({
      ...prev,
      categories: prev.categories.filter(cat => cat !== categorie),
    }));
  };

  const handleCreateThread = async () => {
    await createThread({...threadForm, attachments: threadFiles});
    setThreadForm({title: '', categories: []});
    setThreadFiles([]);
    setThreadDrawerOpen(false);
    setThreadPage(1);
  };

  return (
    <Tabs.Root
      defaultValue="threads"
      fontFamily={'Faculty Glyphic'}
      width="100%">
      <Tabs.List className={styles.tabs_list}>
        <Tabs.Trigger className={styles.tabs_trigger} value="threads" asChild>
          <Link>Threads</Link>
        </Tabs.Trigger>
      </Tabs.List>

      <Tabs.Content value="threads">
        {isAuthenticated === null ? (
          <Text>Loading...</Text>
        ) : isAuthenticated ? (
          <Box>
            <HStack
              alignItems="center"
              gap="3"
              margin="1.5em 0"
              flexWrap="wrap">
              <DrawerRoot
                placement={'bottom'}
                open={threadDrawerOpen}
                onOpenChange={details => setThreadDrawerOpen(details.open)}>
                <DrawerBackdrop />
                <DrawerTrigger asChild>
                  <Button variant="outline" size="sm">
                    <FaPlus />
                    Create new thread
                  </Button>
                </DrawerTrigger>
                <DrawerContent roundedTop={'l3'}>
                  <DrawerHeader>
                    <DrawerTitle>Enter a Thread</DrawerTitle>
                  </DrawerHeader>
                  <DrawerBody>
                    <Textarea
                      placeholder="Your important text"
                      name="title"
                      value={threadForm.title}
                      onChange={handleChange}
                    />
                    <Flex gap="1" margin="0.5rem 0 0.2rem 0">
                      {threadForm.categories?.map((category: string, index) => (
                        <Tag.Root asChild variant="solid" key={index}>
                          <Tag.Label>
                            {category}
                            <RxCross2
                              onClick={() => handleDeleteCategorie(category)}
                            />
                          </Tag.Label>
                        </Tag.Root>
                      ))}
                    </Flex>
                    <Input
                      placeholder="Enter some categories"
                      onKeyDown={handleCategoryKeyDown}
                    />
                    <AttachmentPicker
                      files={threadFiles}
                      inputId="thread-attachments"
                      onChange={setThreadFiles}
                    />
                    {createThreadError ? (
                      <Box color="red.500" marginTop="0.75rem">
                        {createThreadError}
                      </Box>
                    ) : null}
                  </DrawerBody>
                  <DrawerFooter>
                    <DrawerActionTrigger asChild>
                      <Button variant="outline">Cancel</Button>
                    </DrawerActionTrigger>
                    <Button
                      disabled={creatingThread}
                      onClick={handleCreateThread}>
                      {creatingThread ? 'Publishing...' : 'Publish'}
                    </Button>
                  </DrawerFooter>
                  <DrawerCloseTrigger />
                </DrawerContent>
              </DrawerRoot>
              <Box position="relative" flex="1 1 18rem" maxWidth="28rem">
                <Box
                  position="absolute"
                  left="0.75rem"
                  top="50%"
                  transform="translateY(-50%)"
                  color="gray.500"
                  pointerEvents="none">
                  <Search size={16} />
                </Box>
                <Input
                  aria-label="Search threads"
                  value={threadSearch}
                  onChange={event => {
                    setThreadSearch(event.target.value);
                    setThreadPage(1);
                  }}
                  placeholder="Search threads"
                  paddingLeft="2.25rem"
                />
              </Box>
            </HStack>
            <ThreadsTable
              threads={visibleThreads}
              loaded={threadsLoaded}
              error={threadsError}
              emptyTitle={
                normalizedThreadSearch ? 'No matching threads' : 'No threads yet'
              }
              emptyMessage={
                normalizedThreadSearch
                  ? 'Try a different search phrase.'
                  : 'Start the first discussion when you are ready.'
              }
            />
            <Flex
              alignItems="center"
              justifyContent="space-between"
              gap="3"
              marginTop="1rem"
              flexWrap="wrap">
              <Text color="gray.600" fontSize="sm">
                Page {threadPage} of {threadPageCount}
              </Text>
              <Flex gap="2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={threadsLoaded || isFirstThreadPage}
                  onClick={() =>
                    setThreadPage(currentPage => Math.max(1, currentPage - 1))
                  }>
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={threadsLoaded || isLastThreadPage}
                  onClick={() =>
                    setThreadPage(currentPage =>
                      Math.min(threadPageCount, currentPage + 1),
                    )
                  }>
                  Next
                </Button>
              </Flex>
            </Flex>
          </Box>
        ) : (
          <Text>You&#39;re not logged in</Text>
        )}
      </Tabs.Content>
    </Tabs.Root>
  );
};

export default NavigationTabs;
