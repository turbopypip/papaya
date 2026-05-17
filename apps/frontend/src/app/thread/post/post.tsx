'use client';

import React, {FC, useEffect, useState} from 'react';
import {
  Box,
  Button,
  Card,
  Collapsible,
  Flex,
  IconButton,
  Menu,
  Separator,
  Text,
  Textarea,
} from '@chakra-ui/react';
import DOMPurify from 'dompurify';
import {FaPlus} from 'react-icons/fa';
import {EllipsisVertical, Pencil, Trash2, UserRound} from 'lucide-react';
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
import {
  Comment as CommentType,
  CreateCommentRequest,
} from '@/entities/comment/types/commentTypes';
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
import {Attachment, AttachmentGrid, AttachmentPicker} from '@/entities/attachment';
import {useUpdatePost} from '@/entities/post/queries/useUpdatePost';
import {useDeletePost} from '@/entities/post/queries/useDeletePost';
import {useUpdateComment} from '@/entities/comment/queries/useUpdateComment';
import {useDeleteComment} from '@/entities/comment/queries/useDeleteComment';
import {User} from '@/entities/user/types/userTypes';

type Props = {
  post: PostType;
  currentUser: User | null;
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

const AuthorMeta = ({username}: {username?: string}) => (
  <Flex align="center" as="span" gap="1">
    <UserRound size={14} />
    <Text as="span">@{username ?? 'unknown'}</Text>
  </Flex>
);

const CommentItem = ({
  comment,
  currentUser,
}: {
  comment: CommentType;
  currentUser: User | null;
}) => {
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [actionMenuOpen, setActionMenuOpen] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  const [keptAttachments, setKeptAttachments] = useState<Attachment[]>(
    comment.attachments ?? [],
  );
  const [editFiles, setEditFiles] = useState<File[]>([]);
  const {
    updateComment,
    loading: updatingComment,
    error: updateCommentError,
  } = useUpdateComment(comment.post_id);
  const {
    deleteComment,
    loading: deletingComment,
    error: deleteCommentError,
  } = useDeleteComment(comment.post_id);

  const isEdited =
    comment.UpdatedAt &&
    new Date(comment.UpdatedAt).getTime() -
      new Date(comment.CreatedAt).getTime() >
      1000;
  const currentUserId = currentUser?.ID ?? currentUser?.id;
  const commentPermissions = currentUser?.role?.permissions.comments;
  const isCommentOwner = currentUserId === comment.user_id;
  const canEditComment = Boolean(
    commentPermissions?.update_any ||
      (isCommentOwner && commentPermissions?.update_own),
  );
  const canDeleteComment = Boolean(
    commentPermissions?.delete_any ||
      (isCommentOwner && commentPermissions?.delete_own),
  );
  const canManageComment = canEditComment || canDeleteComment;

  useEffect(() => {
    if (!editDrawerOpen) {
      setEditContent(comment.content);
      setKeptAttachments(comment.attachments ?? []);
      setEditFiles([]);
    }
  }, [comment.attachments, comment.content, editDrawerOpen]);

  const openEditDrawer = () => {
    setEditContent(comment.content);
    setKeptAttachments(comment.attachments ?? []);
    setEditFiles([]);
    setEditDrawerOpen(true);
    setActionMenuOpen(false);
  };

  const handleUpdateComment = async () => {
    await updateComment({
      id: comment.ID,
      content: editContent,
      post_id: comment.post_id,
      keep_attachment_ids: keptAttachments.map(attachment => attachment.ID),
      attachments: editFiles,
    });
    setEditDrawerOpen(false);
  };

  const handleDeleteComment = async () => {
    setActionMenuOpen(false);
    if (!window.confirm('Удалить этот комментарий?')) {
      return;
    }

    await deleteComment(comment.ID);
  };

  return (
    <TimelineItem>
      <TimelineConnector />
      <TimelineContent>
        <Flex align="flex-start" gap="3" justify="space-between">
          <TimelineDescription fontFamily="Roboto, Arial, sans-serif">
            <Flex align="center" gap="3" wrap="wrap">
              <AuthorMeta username={comment.author?.username} />
              {isEdited ? (
                <Flex align="center" as="span" gap="1">
                  <Pencil size={14} />
                  {getFormattedDate(comment.UpdatedAt)}
                </Flex>
              ) : (
                getFormattedDate(comment.CreatedAt)
              )}
            </Flex>
          </TimelineDescription>
          {canManageComment ? (
            <Menu.Root
              open={actionMenuOpen}
              onOpenChange={details => setActionMenuOpen(details.open)}>
              <Menu.Trigger asChild>
                <IconButton
                  aria-label="Comment actions"
                  onClick={() => setActionMenuOpen(open => !open)}
                  onMouseEnter={() => setActionMenuOpen(true)}
                  size="xs"
                  variant="ghost">
                  <EllipsisVertical size={16} />
                </IconButton>
              </Menu.Trigger>
              <Menu.Positioner onMouseLeave={() => setActionMenuOpen(false)}>
                <Menu.Content>
                  {canEditComment ? (
                    <Menu.Item onClick={openEditDrawer} value="edit">
                      <Pencil size={16} />
                      Редактировать
                    </Menu.Item>
                  ) : null}
                  {canDeleteComment ? (
                    <Menu.Item
                      color="red.600"
                      disabled={deletingComment}
                      onClick={handleDeleteComment}
                      value="delete">
                      <Trash2 size={16} />
                      Удалить
                    </Menu.Item>
                  ) : null}
                </Menu.Content>
              </Menu.Positioner>
            </Menu.Root>
          ) : null}
        </Flex>

        <Flex align="center" mt="1">
          <Text
            fontFamily="Roboto, Arial, sans-serif"
            textStyle="sm"
            mt="2"
            whiteSpace="pre-wrap"
            overflowWrap="anywhere"
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(comment.content),
            }}
          />
        </Flex>

        <DrawerRoot
          placement={'bottom'}
          open={editDrawerOpen}
          onOpenChange={details => setEditDrawerOpen(details.open)}>
          <DrawerBackdrop />
          <DrawerContent roundedTop={'l3'}>
            <DrawerHeader>
              <DrawerTitle>Редактировать комментарий</DrawerTitle>
            </DrawerHeader>
            <DrawerBody>
              <Textarea
                minH="140px"
                placeholder="Текст комментария"
                value={editContent}
                onChange={event => setEditContent(event.target.value)}
              />
              <Box marginTop="1rem">
                <AttachmentGrid
                  attachments={keptAttachments}
                  onRemove={attachment =>
                    setKeptAttachments(current =>
                      current.filter(item => item.ID !== attachment.ID),
                    )
                  }
                />
              </Box>
              <AttachmentPicker
                files={editFiles}
                inputId={`comment-edit-attachments-${comment.ID}`}
                onChange={setEditFiles}
              />
              {updateCommentError ? (
                <Box color="red.500" marginTop="0.75rem">
                  {updateCommentError}
                </Box>
              ) : null}
            </DrawerBody>
            <DrawerFooter>
              <DrawerActionTrigger asChild>
                <Button variant="outline">Отмена</Button>
              </DrawerActionTrigger>
              <Button disabled={updatingComment} onClick={handleUpdateComment}>
                {updatingComment ? 'Сохраняем...' : 'Сохранить'}
              </Button>
            </DrawerFooter>
            <DrawerCloseTrigger />
          </DrawerContent>
        </DrawerRoot>

        <LikeControl likableType="comment" likableId={comment.ID} />
        <AttachmentGrid attachments={comment.attachments} />
        {deleteCommentError ? (
          <Box color="red.500" marginTop="0.75rem">
            {deleteCommentError}
          </Box>
        ) : null}
      </TimelineContent>
    </TimelineItem>
  );
};

const Post: FC<Props> = ({post, currentUser}) => {
  const [commentForm, setCommentForm] = useState<CreateCommentRequest>({
    content: '',
    post_id: post.ID,
  });
  const [commentFiles, setCommentFiles] = useState<File[]>([]);
  const [opened, setOpened] = useState<boolean>(false);
  const [commentDrawerOpen, setCommentDrawerOpen] = useState(false);
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [actionMenuOpen, setActionMenuOpen] = useState(false);
  const [editContent, setEditContent] = useState(post.content);
  const [keptAttachments, setKeptAttachments] = useState<Attachment[]>(
    post.attachments ?? [],
  );
  const [editFiles, setEditFiles] = useState<File[]>([]);

  const {
    createComment,
    loading: creatingComment,
    error: createCommentError,
  } = useCreateComment();
  const {comments, loaded: commentsLoaded, error: commentsError} =
    useGetCommentsWithPostId(post.ID);
  const {
    updatePost,
    loading: updatingPost,
    error: updatePostError,
  } = useUpdatePost(post.thread_id);
  const {
    deletePost,
    loading: deletingPost,
    error: deletePostError,
  } = useDeletePost(post.thread_id);

  const isEdited =
    post.UpdatedAt &&
    new Date(post.UpdatedAt).getTime() - new Date(post.CreatedAt).getTime() >
      1000;
  const currentUserId = currentUser?.ID ?? currentUser?.id;
  const postPermissions = currentUser?.role?.permissions.posts;
  const isPostOwner = currentUserId === post.user_id;
  const canEditPost = Boolean(
    postPermissions?.update_any || (isPostOwner && postPermissions?.update_own),
  );
  const canDeletePost = Boolean(
    postPermissions?.delete_any || (isPostOwner && postPermissions?.delete_own),
  );
  const canManagePost = canEditPost || canDeletePost;

  useEffect(() => {
    if (!editDrawerOpen) {
      setEditContent(post.content);
      setKeptAttachments(post.attachments ?? []);
      setEditFiles([]);
    }
  }, [editDrawerOpen, post.attachments, post.content]);

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

  const openEditDrawer = () => {
    setEditContent(post.content);
    setKeptAttachments(post.attachments ?? []);
    setEditFiles([]);
    setEditDrawerOpen(true);
    setActionMenuOpen(false);
  };

  const handleUpdatePost = async () => {
    await updatePost({
      id: post.ID,
      content: editContent,
      keep_attachment_ids: keptAttachments.map(attachment => attachment.ID),
      attachments: editFiles,
    });
    setEditDrawerOpen(false);
  };

  const handleDeletePost = async () => {
    setActionMenuOpen(false);
    if (!window.confirm('Удалить этот пост вместе с комментариями?')) {
      return;
    }

    await deletePost(post.ID);
  };

  return (
    <Card.Root marginTop="2em" key={post.ID}>
      <Card.Body gap="2" fontFamily="Roboto, Arial, sans-serif">
        <Flex align="flex-start" gap="3" justify="space-between">
          <Card.Description
            flex="1"
            fontFamily="Roboto, Arial, sans-serif"
            mt="2"
            whiteSpace="pre-wrap"
            overflowWrap="anywhere"
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(post.content),
            }}
          />
          {canManagePost ? (
            <Menu.Root
              open={actionMenuOpen}
              onOpenChange={details => setActionMenuOpen(details.open)}>
              <Menu.Trigger asChild>
                <IconButton
                  aria-label="Post actions"
                  onClick={() => setActionMenuOpen(open => !open)}
                  onMouseEnter={() => setActionMenuOpen(true)}
                  size="sm"
                  variant="ghost">
                  <EllipsisVertical size={18} />
                </IconButton>
              </Menu.Trigger>
              <Menu.Positioner onMouseLeave={() => setActionMenuOpen(false)}>
                <Menu.Content>
                  {canEditPost ? (
                    <Menu.Item onClick={openEditDrawer} value="edit">
                      <Pencil size={16} />
                      Редактировать
                    </Menu.Item>
                  ) : null}
                  {canDeletePost ? (
                    <Menu.Item
                      color="red.600"
                      disabled={deletingPost}
                      onClick={handleDeletePost}
                      value="delete">
                      <Trash2 size={16} />
                      Удалить
                    </Menu.Item>
                  ) : null}
                </Menu.Content>
              </Menu.Positioner>
            </Menu.Root>
          ) : null}
        </Flex>

        <Card.Description
          alignItems="center"
          display="flex"
          gap="3"
          flexWrap="wrap"
          mt="2"
          fontFamily="Roboto, Arial, sans-serif">
          <AuthorMeta username={post.author?.username} />
          {isEdited ? (
            <Flex align="center" as="span" gap="1">
              <Pencil size={14} />
              {getFormattedDate(post.UpdatedAt)}
            </Flex>
          ) : (
            getFormattedDate(post.CreatedAt)
          )}
        </Card.Description>

        <DrawerRoot
          placement={'bottom'}
          open={editDrawerOpen}
          onOpenChange={details => setEditDrawerOpen(details.open)}>
          <DrawerBackdrop />
          <DrawerContent roundedTop={'l3'}>
            <DrawerHeader>
              <DrawerTitle>Редактировать пост</DrawerTitle>
            </DrawerHeader>
            <DrawerBody>
              <Textarea
                minH="180px"
                placeholder="Текст поста"
                value={editContent}
                onChange={event => setEditContent(event.target.value)}
              />
              <Box marginTop="1rem">
                <AttachmentGrid
                  attachments={keptAttachments}
                  onRemove={attachment =>
                    setKeptAttachments(current =>
                      current.filter(item => item.ID !== attachment.ID),
                    )
                  }
                />
              </Box>
              <AttachmentPicker
                files={editFiles}
                inputId={`post-edit-attachments-${post.ID}`}
                onChange={setEditFiles}
              />
              {updatePostError ? (
                <Box color="red.500" marginTop="0.75rem">
                  {updatePostError}
                </Box>
              ) : null}
            </DrawerBody>
            <DrawerFooter>
              <DrawerActionTrigger asChild>
                <Button variant="outline">Отмена</Button>
              </DrawerActionTrigger>
              <Button disabled={updatingPost} onClick={handleUpdatePost}>
                {updatingPost ? 'Сохраняем...' : 'Сохранить'}
              </Button>
            </DrawerFooter>
            <DrawerCloseTrigger />
          </DrawerContent>
        </DrawerRoot>

        <LikeControl likableType="post" likableId={post.ID} />
        <AttachmentGrid attachments={post.attachments} />
        {deletePostError ? (
          <Box color="red.500" marginTop="0.75rem">
            {deletePostError}
          </Box>
        ) : null}

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
                  <CommentItem
                    comment={comment}
                    currentUser={currentUser}
                    key={comment.ID}
                  />
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
