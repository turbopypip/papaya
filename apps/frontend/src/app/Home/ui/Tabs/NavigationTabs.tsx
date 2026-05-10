import React, {useEffect, useState} from 'react';
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
} from '@chakra-ui/react';
import ThreadsTable from '@/app/Home/ui/ThreadsTable/ThreadsTable';
import {useValidate} from '@/entities/user/queries/useValidate';
import {RxCross2} from 'react-icons/rx';
import {CreateThreadRequest, useThreadStore} from '@/entities/thread';
import {usePostThread} from '@/entities/thread/queries/usePostThread';
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

const NavigationTabs = () => {
  const isAuthenticated = useValidate();
  const [threadForm, setThreadForm] = useState<CreateThreadRequest>({
    title: '',
    categories: [],
  });

  const {threads, loaded, error, fetchThreads} = useGetThreads();
  const setThreads = useThreadStore(state => state.setThreads);
  const {createThread, success} = usePostThread();

  useEffect(() => {
    fetchThreads(1, 100);
  }, [success]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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
        {isAuthenticated ? (
          <Box>
            <DrawerRoot placement={'bottom'}>
              <DrawerBackdrop />
              <DrawerTrigger asChild>
                <Button variant="outline" size="sm" margin="1.5em 0 1.5em 0">
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
                </DrawerBody>
                <DrawerFooter>
                  <DrawerActionTrigger asChild>
                    <Button variant="outline">Cancel</Button>
                  </DrawerActionTrigger>
                  <DrawerActionTrigger asChild>
                    <Button onClick={() => createThread(threadForm)}>
                      Publish
                    </Button>
                  </DrawerActionTrigger>
                </DrawerFooter>
                <DrawerCloseTrigger />
              </DrawerContent>
            </DrawerRoot>
            <ThreadsTable
              threads={threads}
              loaded={loaded}
              error={error}
              setThreads={setThreads}
            />
          </Box>
        ) : (
          <Text>You&#39;re not logged in</Text>
        )}
      </Tabs.Content>
    </Tabs.Root>
  );
};

export default NavigationTabs;
