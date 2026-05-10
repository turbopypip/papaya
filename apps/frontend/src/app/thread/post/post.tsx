// vkid-frontend/src/app/thread/post/post.tsx
'use client';

import React, { FC, useEffect, useState } from 'react';
import {
  Button,
  Card,
  Collapsible,
  Separator,
  Text,
  Textarea,
  Flex,
  Box,
} from '@chakra-ui/react';
import getFormattedDate from '@/shared/utils/getFormattedDate';
import {
  TimelineConnector,
  TimelineContent,
  TimelineDescription,
  TimelineItem,
  TimelineRoot,
} from '@/shared/Components/Timeline/ui/timeline';
import { Post as PostType } from '@/entities/post/types/postTypes';
import { useGetCommentsWithPostId } from '@/entities/comment/queries/useGetCommentsWithPostId';
import { CreateCommentRequest } from '@/entities/comment/types/commentTypes';
import { useCreateComment } from '@/entities/comment/queries/useCreateComment';
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
import { FaPlus } from 'react-icons/fa';
import DOMPurify from 'dompurify';

type Props = {
  post: PostType;
};

const Post: FC<Props> = ({ post }) => {
  // ====== Состояние для формы нового комментария ======
  const [commentForm, setCommentForm] = useState<CreateCommentRequest>({
    content: '',
    post_id: post.ID,
  });

  // ====== Мутация для создания комментария ======
  const { createComment, success } = useCreateComment();
  // ====== Хук для получения комментариев по post.ID ======
  const { comments, fetchComments } = useGetCommentsWithPostId();

  // ====== Состояние «открыт/закрыт» раздел комментариев ======
  const [opened, setOpened] = useState<boolean>(false);

  // ====== Лайки для самого поста ======
  // Если у post есть likesCount, используем его, иначе 0
  const initialPostCount =
    typeof (post as any).likesCount === 'number' ? (post as any).likesCount : 0;
  const [postLikesCount, setPostLikesCount] = useState<number>(initialPostCount);
  const [postLiked, setPostLiked] = useState<boolean>(false);

  // Обработчик лайка для поста (отдельные setState, чтобы не было двойного апдейта)
  const handlePostLike = () => {
    if (!postLiked) {
      setPostLiked(true);
      setPostLikesCount((c) => c + 1);
    } else {
      setPostLiked(false);
      setPostLikesCount((c) => Math.max(c - 1, 0));
    }
  };

  // ====== Лайки для каждого комментария ======
  // Структура: { [commentID]: { liked: boolean; count: number } }
  const [commentLikes, setCommentLikes] = useState<{
    [key: number]: { liked: boolean; count: number };
  }>({});

  // При загрузке комментариев инициализируем состояния likes для них
  useEffect(() => {
    if (comments && comments.length > 0) {
      setCommentLikes((prev) => {
        const updated = { ...prev };
        comments.forEach((c) => {
          if (typeof updated[c.ID] === 'undefined') {
            const initialCount =
              typeof (c as any).likesCount === 'number' ? (c as any).likesCount : 0;
            updated[c.ID] = { liked: false, count: initialCount };
          }
        });
        return updated;
      });
    }
  }, [comments]);

  // Обработчик лайка для комментария по его ID
  const handleCommentLike = (commentId: number) => {
    setCommentLikes((prev) => {
      const current = prev[commentId];
      if (!current) {
        // На всякий случай: если нет ключа, создаём
        return {
          ...prev,
          [commentId]: { liked: true, count: 1 },
        };
      }
      if (!current.liked) {
        // Ставим лайк
        return {
          ...prev,
          [commentId]: { liked: true, count: current.count + 1 },
        };
      } else {
        // Убираем лайк
        return {
          ...prev,
          [commentId]: { liked: false, count: Math.max(current.count - 1, 0) },
        };
      }
    });
  };

  // ====== Загрузка комментариев (перезагрузка при success) ======
  useEffect(() => {
    fetchComments(post.ID, 1, 100);
  }, [success]);

  // ====== Обработчик изменения textarea (форма комментария) ======
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setCommentForm((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <Card.Root marginTop="2em" key={post.ID}>
      <Card.Body gap="2">
        {/* ====== ТЕКСТ ПОСТА ====== */}
        <Card.Description
          mt="2"
          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(post.content) }}
        />

        {/* ====== ДАТА ПУБЛИКАЦИИ ====== */}
        <Card.Description mt="2" fontFamily="Faculty Glyphic">
          {getFormattedDate(post.CreatedAt)}
        </Card.Description>

        {/* ====== БЛОК «ЛАЙК» ДЛЯ ПОСТА ====== */}
        <Flex align="center" mt="1">
          <Button
            aria-label={postLiked ? 'Убрать лайк' : 'Поставить лайк'}
            onClick={handlePostLike}
            variant="ghost"
            size="sm"
            color={postLiked ? 'red.500' : 'gray.500'}
            fontSize="20px"
            px="1"
            _hover={{ bg: 'transparent' }}
          >
            {postLiked ? '♥' : '♡'}
          </Button>
          <Box ml="1" fontSize="sm">
            {postLikesCount}
          </Box>
        </Flex>

        {/* ====== СЕКЦИЯ КОММЕНТАРИЕВ ====== */}
        <Card.Footer padding="0">
          <Collapsible.Root
            width="100%"
            onOpenChange={() => setOpened((o) => !o)}
          >
            <Collapsible.Trigger>
              <Button variant="outline" margin="1.5rem 0 1.5rem 0">
                {opened ? 'Close' : 'View comments'}
              </Button>
            </Collapsible.Trigger>

            <Collapsible.Content>
              <Separator margin="1em 0 1em 0" />

              <TimelineRoot>
                {/* ====== КНОПКА «Write a comment» (Drawer) ====== */}
                <DrawerRoot placement={'bottom'}>
                  <DrawerBackdrop />
                  <DrawerTrigger asChild width="fit-content">
                    <Button
                      variant="outline"
                      size="sm"
                      margin="1.5em 0 1.5em 0"
                    >
                      <FaPlus style={{ marginRight: '0.5rem' }} />
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
                    </DrawerBody>
                    <DrawerFooter>
                      <DrawerActionTrigger asChild>
                        <Button variant="outline">Cancel</Button>
                      </DrawerActionTrigger>
                      <DrawerActionTrigger asChild>
                        <Button onClick={() => createComment(commentForm)}>
                          Publish
                        </Button>
                      </DrawerActionTrigger>
                    </DrawerFooter>
                    <DrawerCloseTrigger />
                  </DrawerContent>
                </DrawerRoot>

                {/* ====== СПИСОК КОММЕНТАРИЕВ (каждый с «лайком») ====== */}
                {comments?.map((comment) => (
                  <TimelineItem key={comment.ID}>
                    <TimelineConnector />
                    <TimelineContent>
                      <TimelineDescription fontFamily="Faculty Glyphic">
                        {getFormattedDate(comment.CreatedAt)}
                      </TimelineDescription>
                      <Flex align="center" mt="1">
                        <Text textStyle="sm"
                          mt="2"
                          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comment.content) }}
                        />
                      </Flex>
                      <Flex>
                        <Button
                          aria-label={
                            commentLikes[comment.ID]?.liked
                              ? 'Убрать лайк'
                              : 'Поставить лайк'
                          }
                          onClick={() => handleCommentLike(comment.ID)}
                          variant="ghost"
                          size="sm"
                          color={
                            commentLikes[comment.ID]?.liked
                              ? 'red.500'
                              : 'gray.500'
                          }
                          fontSize="20px"
                          ml="2"
                          px="1"
                          _hover={{ bg: 'transparent' }}
                        >
                          {commentLikes[comment.ID]?.liked ? '♥' : '♡'}
                        </Button>
                        <Box ml="1" fontSize="sm">
                          {postLikesCount}
                        </Box>
                      </Flex>
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
