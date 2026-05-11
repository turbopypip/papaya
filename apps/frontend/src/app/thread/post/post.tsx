'use client';

import React, {FC, useState} from 'react';
import {
  Box,
  Button,
  Card,
  Collapsible,
  Flex,
  Separator,
  Text,
  Textarea,
} from '@chakra-ui/react';
import DOMPurify from 'dompurify';
import {FaPlus} from 'react-icons/fa';
import getFormattedDate from '@/shared/utils/getFormattedDate';
import {
  TimelineConnector,
  TimelineContent,
  TimelineDescription,
  TimelineItem,
  TimelineRoot,
} from '@/shared/Components/Timeline/ui/timeline';
import {Post as PostType} from '@/entities/post/types/postTypes';
import {useGetCommentsWithPostId} from '@/entities/comment/queries/useGetCommentsWithPostId';
import {CreateCommentRequest} from '@/entities/comment/types/commentTypes';
import {useCreateComment} from '@/entities/comment/queries/useCreateComment';
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
import {LikableType, useLike} from '@/entities/like';
import {AttachmentGrid, AttachmentPicker} from '@/entities/attachment';

type Props = {
  post: PostType;
};

const LikeControl = ({
  likableType,
  likableId,
}: {
  likableType: LikableType;
  likableId: string;
}) => {
  const {count, likedByMe, loading, toggleLike} = useLike(
    likableType,
    likableId,
  );

  return (
    <Flex align="center" mt="1">
      <Button
        aria-label={likedByMe ? 'Убрать лайк' : 'Поставить лайк'}
        onClick={() => toggleLike()}
        disabled={loading}
        variant="ghost"
        size="sm"
        color={likedByMe ? 'red.500' : 'gray.500'}
        fontSize="20px"
        px="1"
        _hover={{bg: 'transparent'}}>
        {likedByMe ? '♥' : '♡'}
      </Button>
      <Box ml="1" fontSize="sm">
        {count}
      </Box>
    </Flex>
  );
};

const Post: FC<Props> = ({post}) => {
  const [commentForm, setCommentForm] = useState<CreateCommentRequest>({
    content: '',
    post_id: post.ID,
  });
  const [commentFiles, setCommentFiles] = useState<File[]>([]);
  const [opened, setOpened] = useState<boolean>(false);
  const [commentDrawerOpen, setCommentDrawerOpen] = useState(false);

  const {
    createComment,
    loading: creatingComment,
    error: createCommentError,
  } = useCreateComment();
  const {comments, loaded: commentsLoaded, error: commentsError} =
    useGetCommentsWithPostId(post.ID);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const {name, value} = e.target;
    setCommentForm(prev => ({...prev, [name]: value}));
  };

  const handleCreateComment = async () => {
    await createComment({...commentForm, attachments: commentFiles});
    setCommentForm({content: '', post_id: post.ID});
    setCommentFiles([]);
    setCommentDrawerOpen(false);
  };

  return (
    <Card.Root marginTop="2em" key={post.ID}>
      <Card.Body gap="2" fontFamily="Roboto, Arial, sans-serif">
        <Card.Description
          fontFamily="Roboto, Arial, sans-serif"
          mt="2"
          dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(post.content)}}
        />

        <Card.Description mt="2" fontFamily="Roboto, Arial, sans-serif">
          {getFormattedDate(post.CreatedAt)}
        </Card.Description>

        <LikeControl likableType="post" likableId={post.ID} />
        <AttachmentGrid attachments={post.attachments} />

        <Card.Footer padding="0">
          <Collapsible.Root
            width="100%"
            onOpenChange={() => setOpened(o => !o)}>
            <Collapsible.Trigger>
              <Button variant="outline" margin="1.5rem 0 1.5rem 0">
                {opened ? 'Close' : 'View comments'}
              </Button>
            </Collapsible.Trigger>

            <Collapsible.Content>
              <Separator margin="1em 0 1em 0" />

              <TimelineRoot>
                <DrawerRoot
                  placement={'bottom'}
                  open={commentDrawerOpen}
                  onOpenChange={details => setCommentDrawerOpen(details.open)}>
                  <DrawerBackdrop />
                  <DrawerTrigger asChild width="fit-content">
                    <Button
                      variant="outline"
                      size="sm"
                      margin="1.5em 0 1.5em 0">
                      <FaPlus style={{marginRight: '0.5rem'}} />
                      Write a comment
                    </Button>
                  </DrawerTrigger>
                  <DrawerContent roundedTop={'l3'}>
                    <DrawerHeader>
                      <DrawerTitle>Enter a comment</DrawerTitle>
                    </DrawerHeader>
                    <DrawerBody>
                      <Textarea
                        placeholder="Your important comment"
                        name="content"
                        value={commentForm.content}
                        onChange={handleChange}
                      />
                      <AttachmentPicker
                        files={commentFiles}
                        inputId={`comment-attachments-${post.ID}`}
                        onChange={setCommentFiles}
                      />
                      {createCommentError ? (
                        <Box color="red.500" marginTop="0.75rem">
                          {createCommentError}
                        </Box>
                      ) : null}
                    </DrawerBody>
                    <DrawerFooter>
                      <DrawerActionTrigger asChild>
                        <Button variant="outline">Cancel</Button>
                      </DrawerActionTrigger>
                      <Button
                        disabled={creatingComment}
                        onClick={handleCreateComment}>
                        {creatingComment ? 'Publishing...' : 'Publish'}
                      </Button>
                    </DrawerFooter>
                    <DrawerCloseTrigger />
                  </DrawerContent>
                </DrawerRoot>

                {commentsLoaded ? <Box>Loading comments...</Box> : null}
                {commentsError ? (
                  <Box color="red.500">{commentsError}</Box>
                ) : null}

                {comments?.map(comment => (
                  <TimelineItem key={comment.ID}>
                    <TimelineConnector />
                    <TimelineContent>
                      <TimelineDescription fontFamily="Roboto, Arial, sans-serif">
                        {getFormattedDate(comment.CreatedAt)}
                      </TimelineDescription>
                      <Flex align="center" mt="1">
                        <Text
                          fontFamily="Roboto, Arial, sans-serif"
                          textStyle="sm"
                          mt="2"
                          dangerouslySetInnerHTML={{
                            __html: DOMPurify.sanitize(comment.content),
                          }}
                        />
                      </Flex>
                      <LikeControl
                        likableType="comment"
                        likableId={comment.ID}
                      />
                      <AttachmentGrid attachments={comment.attachments} />
                    </TimelineContent>
                  </TimelineItem>
                ))}
              </TimelineRoot>
            </Collapsible.Content>
          </Collapsible.Root>
        </Card.Footer>
      </Card.Body>
    </Card.Root>
  );
};

export default Post;
