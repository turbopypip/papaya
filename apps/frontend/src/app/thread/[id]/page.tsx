'use client';
import React, {useDeferredValue, useEffect, useRef, useState} from 'react';
import {
  Box,
  Container,
  Card,
  Separator,
  Link,
  Button,
  Textarea,
  Input,
  Flex,
  IconButton,
  Menu,
  Text,
} from '@chakra-ui/react';
import getFormattedDate from '@/shared/utils/getFormattedDate';
import {Tag} from '@/shared/Components/Tag/ui/tag';
import {useGetPosts} from '@/entities/post/queries/useGetPosts';
import {LiaSlashSolid} from 'react-icons/lia';
import {
  BreadcrumbCurrentLink,
  BreadcrumbRoot,
} from '@/shared/Components/Breadcrumb/ui/breadcrumb';
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
import {FaPlus} from 'react-icons/fa';
import {useCreatePost} from '@/entities/post/queries/useCreatePost';
import {CreatePostRequest} from '@/entities/post/types/postTypes';
import Post from '@/app/thread/post/post';
import {useGetThread} from '@/entities/thread/queries/useGetThread';
import {useThreadEvents} from '@/entities/thread/queries/useThreadEvents';
import {AttachmentGrid, AttachmentPicker} from '@/entities/attachment';
import {useValidate} from '@/entities/user/queries/useValidate';
import {useUpdateThread} from '@/entities/thread/queries/useUpdateThread';
import {useDeleteThread} from '@/entities/thread/queries/useDeleteThread';
import {UpdateThreadRequest} from '@/entities/thread/types/threadTypes';
import {
  Pencil,
  Trash2,
  Check,
  X,
  EllipsisVertical,
  UserRound,
  Search,
} from 'lucide-react';
import {useRouter} from 'next/navigation';
import {useGetCurrentUser} from '@/entities/user/queries/useGetCurrentUser';
import {MarkdownEditor} from '@/shared/Components/Markdown';
import {StatePanel} from '@/shared/Components/StatePanel';
import {useSearchPosts} from '@/entities/post/queries/useSearchPosts';
import {recordThreadView} from '@/entities/thread/api/recordThreadView';

const ThreadPage = ({params}: {params: {id: string}}) => {
  const router = useRouter();
  const isAuthenticated = useValidate();
  const canFetchThread = isAuthenticated === true;

  useThreadEvents(params.id, canFetchThread);

  const {
    thread,
    deletedThread,
    loaded: threadLoaded,
    error: threadError,
  } = useGetThread(params.id, canFetchThread);
  const {
    posts,
    loaded: postsLoaded,
    loadingMore: postsLoadingMore,
    hasMore: hasMorePosts,
    loadMore: loadMorePosts,
    error: postsError,
  } = useGetPosts(params.id, canFetchThread);
  const [postSearch, setPostSearch] = useState('');
  const deferredPostSearch = useDeferredValue(postSearch);
  const normalizedPostSearch = deferredPostSearch.trim();
  const {
    posts: foundPosts,
    loaded: searchPostsLoaded,
    error: searchPostsError,
  } = useSearchPosts(params.id, deferredPostSearch, canFetchThread);
  const {user: currentUser} = useGetCurrentUser(canFetchThread);

  const [postForm, setPostForm] = useState<CreatePostRequest>({
    content: '',
    thread_id: params.id,
  });
  const [postFiles, setPostFiles] = useState<File[]>([]);
  const [postDrawerOpen, setPostDrawerOpen] = useState(false);
  const postsLoadMoreRef = useRef<HTMLDivElement | null>(null);
  const [isEditingThread, setIsEditingThread] = useState(false);
  const [threadActionMenuOpen, setThreadActionMenuOpen] = useState(false);
  const [threadForm, setThreadForm] = useState<UpdateThreadRequest>({
    id: params.id,
    title: '',
    categories: [],
  });
  const [threadFiles, setThreadFiles] = useState<File[]>([]);
  const trackedThreadViewRef = useRef<string | null>(null);

  const {
    createPost,
    loading: creatingPost,
    error: createPostError,
  } = useCreatePost(params.id);
  const {
    updateThread,
    loading: updatingThread,
    error: updateThreadError,
  } = useUpdateThread();
  const {
    deleteThread,
    loading: deletingThread,
    error: deleteThreadError,
  } = useDeleteThread();

  useEffect(() => {
    setPostForm(prev => ({...prev, thread_id: params.id}));
  }, [params.id]);

  useEffect(() => {
    if (!thread) {
      return;
    }

    setThreadForm({
      id: thread.ID,
      title: thread.title,
      categories: thread.categories ?? [],
      keep_attachment_ids: thread.attachments?.map(attachment => attachment.ID),
    });
    setThreadFiles([]);
    setIsEditingThread(false);
  }, [thread]);

  useEffect(() => {
    if (!canFetchThread || !thread || trackedThreadViewRef.current === thread.ID) {
      return;
    }

    trackedThreadViewRef.current = thread.ID;
    void recordThreadView(thread.ID).catch(() => {
      trackedThreadViewRef.current = null;
    });
  }, [canFetchThread, thread]);

  useEffect(() => {
    const target = postsLoadMoreRef.current;
    if (
      !target ||
      normalizedPostSearch ||
      !hasMorePosts ||
      postsLoadingMore ||
      !canFetchThread
    ) {
      return;
    }

    const observer = new IntersectionObserver(entries => {
      if (entries[0]?.isIntersecting) {
        loadMorePosts();
      }
    });

    observer.observe(target);

    return () => observer.disconnect();
  }, [
    canFetchThread,
    hasMorePosts,
    loadMorePosts,
    normalizedPostSearch,
    postsLoadingMore,
  ]);

  const handleCreatePost = async () => {
    await createPost({...postForm, attachments: postFiles});
    setPostForm({content: '', thread_id: params.id});
    setPostFiles([]);
    setPostDrawerOpen(false);
  };

  const handleThreadChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const {name, value} = e.target;
    setThreadForm(prev => ({...prev, [name]: value}));
  };

  const handleThreadCategoryKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (e.key !== 'Enter') {
      return;
    }

    e.preventDefault();
    const input = e.currentTarget.value.trim();
    if (input && !threadForm.categories.includes(input)) {
      setThreadForm(prev => ({
        ...prev,
        categories: [...prev.categories, input],
      }));
    }
    e.currentTarget.value = '';
  };

  const handleDeleteThreadCategory = (category: string) => {
    setThreadForm(prev => ({
      ...prev,
      categories: prev.categories.filter(current => current !== category),
    }));
  };

  const handleCancelThreadEdit = () => {
    if (!thread) {
      return;
    }

    setThreadForm({
      id: thread.ID,
      title: thread.title,
      categories: thread.categories ?? [],
      keep_attachment_ids: thread.attachments?.map(attachment => attachment.ID),
    });
    setThreadFiles([]);
    setIsEditingThread(false);
  };

  const handleUpdateThread = async () => {
    const keepAttachmentIds =
      thread?.attachments?.map(attachment => attachment.ID) ?? [];

    await updateThread({
      ...threadForm,
      keep_attachment_ids: keepAttachmentIds,
      attachments: threadFiles,
    });
    setThreadFiles([]);
    setIsEditingThread(false);
  };

  const handleDeleteThread = async () => {
    setThreadActionMenuOpen(false);
    const confirmed = window.confirm(
      'Удалить тред вместе со всеми постами и комментариями?',
    );
    if (!confirmed) {
      return;
    }

    await deleteThread(params.id);
    router.push('/');
  };

  if (isAuthenticated === null) {
    return (
      <Container>
        <StatePanel title="Загружаем сессию">
          Проверяем доступ перед открытием треда.
        </StatePanel>
      </Container>
    );
  }

  if (!isAuthenticated) {
    return (
      <Container>
        <StatePanel title="Вы не вошли в аккаунт">
          Войдите, чтобы смотреть обсуждения.
        </StatePanel>
      </Container>
    );
  }

  if (threadLoaded) {
    return (
      <Container>
        <StatePanel title="Загружаем тред">
          Получаем актуальные данные треда.
        </StatePanel>
      </Container>
    );
  }

  if (threadError) {
    return (
      <Container>
        <StatePanel title="Не удалось загрузить тред" tone="danger">
          {threadError}
        </StatePanel>
      </Container>
    );
  }

  if (deletedThread) {
    return (
      <Container>
        <Card.Root marginTop="2rem">
          <Card.Body gap="2" fontFamily="Roboto, Arial, sans-serif">
            <Card.Title>Тред удалён</Card.Title>
            <Card.Description>
              Этот тред был удален {getFormattedDate(deletedThread.deleted_at)}.
            </Card.Description>
          </Card.Body>
        </Card.Root>
      </Container>
    );
  }

  if (thread == null) {
    return (
      <Container>
        <StatePanel title="Тред не найден">
          Возможно, он удалён или ссылка устарела.
        </StatePanel>
      </Container>
    );
  }

  const currentUserId = currentUser?.ID ?? currentUser?.id;
  const threadPermissions = currentUser?.role?.permissions.threads;
  const isThreadOwner = currentUserId === thread.user_id;
  const canEditThread = Boolean(
    threadPermissions?.update_any ||
      (isThreadOwner && threadPermissions?.update_own),
  );
  const canDeleteThread = Boolean(
    threadPermissions?.delete_any ||
      (isThreadOwner && threadPermissions?.delete_own),
  );
  const canManageThread = canEditThread || canDeleteThread;
  const isThreadEdited =
    thread.UpdatedAt &&
    new Date(thread.UpdatedAt).getTime() -
      new Date(thread.CreatedAt).getTime() >
      1000;
  const visiblePosts = normalizedPostSearch ? foundPosts : posts;
  const visiblePostsLoaded = normalizedPostSearch
    ? searchPostsLoaded
    : postsLoaded;
  const visiblePostsError = normalizedPostSearch
    ? searchPostsError
    : postsError;

  return (
    <Container>
      <BreadcrumbRoot
        separator={<LiaSlashSolid />}
        marginTop="2rem"
        fontFamily="Faculty Glyphic">
        <Link href="/" fontSize="18px">
          Треды
        </Link>
        <BreadcrumbCurrentLink
          fontSize="18px"
          whiteSpace="pre-wrap"
          overflowWrap="anywhere">
          {thread.title}
        </BreadcrumbCurrentLink>
      </BreadcrumbRoot>
      <DrawerRoot
        placement={'bottom'}
        open={postDrawerOpen}
        onOpenChange={details => setPostDrawerOpen(details.open)}>
        <DrawerBackdrop />
        <DrawerTrigger asChild>
          <Button variant="outline" size="sm" margin="1.5em 0 1.5em 0">
            <FaPlus />
            Создать пост
          </Button>
        </DrawerTrigger>
        <DrawerContent roundedTop={'l3'}>
          <DrawerHeader>
            <DrawerTitle>Новый пост</DrawerTitle>
          </DrawerHeader>
          <DrawerBody>
            <MarkdownEditor
              placeholder="Поделитесь кодом, контекстом и тем, что уже пробовали"
              value={postForm.content}
              onChange={content => setPostForm(prev => ({...prev, content}))}
            />
            <AttachmentPicker
              files={postFiles}
              inputId="post-attachments"
              onChange={setPostFiles}
            />
            {createPostError ? (
              <Box color="red.500" marginTop="0.75rem">
                {createPostError}
              </Box>
            ) : null}
          </DrawerBody>
          <DrawerFooter>
            <DrawerActionTrigger asChild>
              <Button variant="outline">Отмена</Button>
            </DrawerActionTrigger>
            <Button disabled={creatingPost} onClick={handleCreatePost}>
              {creatingPost ? 'Публикуем...' : 'Опубликовать'}
            </Button>
          </DrawerFooter>
          <DrawerCloseTrigger />
        </DrawerContent>
      </DrawerRoot>
      <Card.Root marginTop="1em">
        <Card.Body gap="2" fontFamily="Roboto, Arial, sans-serif">
          {isEditingThread ? (
            <Box display="grid" gap="0.75rem">
              <Textarea
                disabled={updatingThread}
                name="title"
                value={threadForm.title}
                onChange={handleThreadChange}
              />
              <Flex gap="2" wrap="wrap">
                {threadForm.categories.map(category => (
                  <Button
                    key={category}
                    variant="outline"
                    size="xs"
                    disabled={updatingThread}
                    onClick={() => handleDeleteThreadCategory(category)}>
                    <X size={14} />
                    {category}
                  </Button>
                ))}
              </Flex>
              <Input
                disabled={updatingThread}
                placeholder="Введите категорию и нажмите Enter"
                onKeyDown={handleThreadCategoryKeyDown}
              />
              <AttachmentGrid attachments={thread.attachments} />
              <AttachmentPicker
                files={threadFiles}
                inputId="thread-edit-attachments"
                onChange={setThreadFiles}
              />
              {updateThreadError ? (
                <Box color="red.500">{updateThreadError}</Box>
              ) : null}
              <Flex gap="2" justifyContent="flex-end">
                <Button
                  variant="outline"
                  onClick={handleCancelThreadEdit}
                  disabled={updatingThread}>
                  <X size={16} />
                  Отмена
                </Button>
                <Button onClick={handleUpdateThread} disabled={updatingThread}>
                  <Check size={16} />
                  {updatingThread ? 'Сохраняем...' : 'Сохранить'}
                </Button>
              </Flex>
            </Box>
          ) : (
            <>
              <Flex
                justifyContent="space-between"
                alignItems="flex-start"
                gap="3">
                <Card.Title
                  mt="2"
                  fontFamily="Roboto, Arial, sans-serif"
                  whiteSpace="pre-wrap"
                  overflowWrap="anywhere">
                  {thread.title}
                </Card.Title>
                {canManageThread ? (
                  <Menu.Root
                    open={threadActionMenuOpen}
                    onOpenChange={details =>
                      setThreadActionMenuOpen(details.open)
                    }>
                    <Menu.Trigger asChild>
                      <IconButton
                        aria-label="Действия с тредом"
                        onClick={() => setThreadActionMenuOpen(open => !open)}
                        onMouseEnter={() => setThreadActionMenuOpen(true)}
                        size="sm"
                        variant="ghost">
                        <EllipsisVertical size={18} />
                      </IconButton>
                    </Menu.Trigger>
                    <Menu.Positioner
                      onMouseLeave={() => setThreadActionMenuOpen(false)}>
                      <Menu.Content>
                        {canEditThread ? (
                          <Menu.Item
                            onClick={() => {
                              setIsEditingThread(true);
                              setThreadActionMenuOpen(false);
                            }}
                            value="edit">
                            <Pencil size={16} />
                            Редактировать
                          </Menu.Item>
                        ) : null}
                        {canDeleteThread ? (
                          <Menu.Item
                            color="red.600"
                            disabled={deletingThread}
                            onClick={handleDeleteThread}
                            value="delete">
                            <Trash2 size={16} />
                            {deletingThread ? 'Удаляем...' : 'Удалить'}
                          </Menu.Item>
                        ) : null}
                      </Menu.Content>
                    </Menu.Positioner>
                  </Menu.Root>
                ) : null}
              </Flex>
              <Card.Description>
                <Box display="flex" gap="2">
                  {(thread.categories ?? []).map(categorie => (
                    <Tag key={categorie} colorScheme="purple">
                      {categorie}
                    </Tag>
                  ))}
                </Box>
              </Card.Description>
              <Card.Description mt="2" fontFamily="Roboto, Arial, sans-serif">
                <Flex align="center" gap="3" wrap="wrap">
                  <Flex align="center" as="span" gap="1">
                    <UserRound size={14} />
                    <Text as="span">
                      @{thread.author?.username ?? 'неизвестно'}
                    </Text>
                  </Flex>
                  {isThreadEdited ? (
                    <Flex align="center" as="span" gap="1">
                      <Pencil size={14} />
                      {getFormattedDate(thread.UpdatedAt)}
                    </Flex>
                  ) : (
                    getFormattedDate(thread.CreatedAt)
                  )}
                </Flex>
              </Card.Description>
              <AttachmentGrid attachments={thread.attachments} />
              {deleteThreadError ? (
                <Box color="red.500" marginTop="0.75rem">
                  {deleteThreadError}
                </Box>
              ) : null}
            </>
          )}
        </Card.Body>
      </Card.Root>
      {createPostError ? <Box color="red.500">{createPostError}</Box> : null}
      <Box marginTop="1.5rem" position="relative" maxWidth="32rem">
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
          aria-label="Поиск постов в этом треде"
          value={postSearch}
          onChange={event => setPostSearch(event.target.value)}
          placeholder="Поиск постов в этом треде"
          paddingLeft="2.25rem"
        />
      </Box>
      {visiblePostsLoaded ? (
        <StatePanel title="Загружаем посты">
          Загружаем ответы в этом треде.
        </StatePanel>
      ) : visiblePostsError ? (
        <StatePanel title="Не удалось загрузить посты" tone="danger">
          {visiblePostsError}
        </StatePanel>
      ) : visiblePosts.length > 0 ? (
        <Box marginBottom="2rem">
          <Separator margin="2em 0 2em 0" />
          {visiblePosts.map(post => (
            <Post key={post.ID} post={post} currentUser={currentUser} />
          ))}
          {!normalizedPostSearch ? (
            <Box ref={postsLoadMoreRef} minHeight="1px">
              {postsLoadingMore ? (
                <StatePanel title="Загружаем ещё посты">
                  Загружаем следующие ответы.
                </StatePanel>
              ) : null}
            </Box>
          ) : null}
        </Box>
      ) : (
        <StatePanel
          title={
            normalizedPostSearch ? 'Подходящих постов нет' : 'Пока нет постов'
          }>
          {normalizedPostSearch
            ? 'Попробуйте изменить поисковый запрос.'
            : 'Добавьте первый контекст, код или ответ.'}
        </StatePanel>
      )}
    </Container>
  );
};

export default ThreadPage;
