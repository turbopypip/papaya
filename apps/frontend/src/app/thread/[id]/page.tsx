'use client';
import React, {useEffect, useState} from 'react';
import {
  Box,
  Container,
  Card,
  Separator,
  Link,
  Button,
  Textarea,
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

const ThreadPage = ({params}: {params: {id: string}}) => {
  useThreadEvents(params.id);

  const {
    thread,
    deletedThread,
    loaded: threadLoaded,
    error: threadError,
  } = useGetThread(params.id);
  const {posts, loaded: postsLoaded, error: postsError} = useGetPosts(
    params.id,
  );

  const [postForm, setPostForm] = useState<CreatePostRequest>({
    content: '',
    thread_id: params.id,
  });
  const [postFiles, setPostFiles] = useState<File[]>([]);
  const [postDrawerOpen, setPostDrawerOpen] = useState(false);

  const {createPost, loading: creatingPost, error: createPostError} =
    useCreatePost(params.id);

  useEffect(() => {
    setPostForm(prev => ({...prev, thread_id: params.id}));
  }, [params.id]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const {name, value} = e.target;
    setPostForm(prev => ({...prev, [name]: value}));
  };

  const handleCreatePost = async () => {
    await createPost({...postForm, attachments: postFiles});
    setPostForm({content: '', thread_id: params.id});
    setPostFiles([]);
    setPostDrawerOpen(false);
  };

  if (threadLoaded) {
    return <Container>Loading...</Container>;
  }

  if (threadError) {
    return <Container>{threadError}</Container>;
  }

  if (deletedThread) {
    return (
      <Container>
        <Card.Root marginTop="2rem">
          <Card.Body gap="2" fontFamily="Roboto, Arial, sans-serif">
            <Card.Title>Тред удален</Card.Title>
            <Card.Description>
              Этот тред был удален {getFormattedDate(deletedThread.deleted_at)}.
            </Card.Description>
          </Card.Body>
        </Card.Root>
      </Container>
    );
  }

  if (thread == null) {
    return <>Not found this thread</>;
  }

  return (
    <Container>
      <BreadcrumbRoot
        separator={<LiaSlashSolid />}
        marginTop="2rem"
        fontFamily="Faculty Glyphic">
        <Link href="/" fontSize="18px">
          Threads
        </Link>
        <BreadcrumbCurrentLink fontSize="18px">
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
            Create new post
          </Button>
        </DrawerTrigger>
        <DrawerContent roundedTop={'l3'}>
          <DrawerHeader>
            <DrawerTitle>Enter a post</DrawerTitle>
          </DrawerHeader>
          <DrawerBody>
            <Textarea
              placeholder="Your important post"
              name="content"
              value={postForm.content}
              onChange={handleChange}
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
              <Button variant="outline">Cancel</Button>
            </DrawerActionTrigger>
            <Button
              disabled={creatingPost}
              onClick={handleCreatePost}>
              {creatingPost ? 'Publishing...' : 'Publish'}
            </Button>
          </DrawerFooter>
          <DrawerCloseTrigger />
        </DrawerContent>
      </DrawerRoot>
      <Card.Root marginTop="1em">
        <Card.Body gap="2" fontFamily="Roboto, Arial, sans-serif">
          <Card.Title mt="2" fontFamily="Roboto, Arial, sans-serif">
            {thread.title}
          </Card.Title>
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
            {getFormattedDate(thread.CreatedAt)}
          </Card.Description>
          <AttachmentGrid attachments={thread.attachments} />
        </Card.Body>
      </Card.Root>
      {createPostError ? (
        <Box color="red.500">{createPostError}</Box>
      ) : null}
      {postsLoaded ? (
        <Box>Loading posts...</Box>
      ) : postsError ? (
        <Box color="red.500">{postsError}</Box>
      ) : posts.length > 0 ? (
        <Box marginBottom="2rem">
          <Separator margin="2em 0 2em 0" />
          {posts.map(post => (
            <Post key={post.ID} post={post} />
          ))}
        </Box>
      ) : (
        <Box>This thread has no posts</Box>
      )}
    </Container>
  );
};

export default ThreadPage;
