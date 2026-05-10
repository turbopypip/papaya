'use client';
import React, {useEffect, useState} from 'react';
import {useThreadStore} from '@/entities/thread/stores/threadStore';
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

const ThreadPage = ({params}: {params: {id: string}}) => {
  const thread = useThreadStore(state => state.threads).find(
    thread => thread.ID === params.id,
  );

  const {posts, loaded, error, fetchPosts} = useGetPosts(params.id);

  const [postForm, setPostForm] = useState<CreatePostRequest>({
    content: '',
    thread_id: thread ? thread.ID : '',
  });

  const {createPost, success} = useCreatePost();

  useEffect(() => {
    fetchPosts(1, 100);
  }, [success]);
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const {name, value} = e.target;
    setPostForm(prev => ({...prev, [name]: value}));
  };

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
      <DrawerRoot placement={'bottom'}>
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
          </DrawerBody>
          <DrawerFooter>
            <DrawerActionTrigger asChild>
              <Button variant="outline">Cancel</Button>
            </DrawerActionTrigger>
            <DrawerActionTrigger asChild>
              <Button onClick={() => createPost(postForm)}>Publish</Button>
            </DrawerActionTrigger>
          </DrawerFooter>
          <DrawerCloseTrigger />
        </DrawerContent>
      </DrawerRoot>
      <Card.Root marginTop="1em">
        <Card.Body gap="2">
          <Card.Title mt="2" fontFamily="Faculty Glyphic">
            {thread.title}
          </Card.Title>
          <Card.Description>
            <Box display="flex" gap="2">
              {thread.categories.map(categorie => (
                <Tag key={categorie} colorScheme="purple">
                  {categorie}
                </Tag>
              ))}
            </Box>
          </Card.Description>
          <Card.Description mt="2" fontFamily="Faculty Glyphic">
            {getFormattedDate(thread.CreatedAt)}
          </Card.Description>
        </Card.Body>
      </Card.Root>
      {posts.length > 0 ? (
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
