// vkid-frontend-main/vkid-frontend/src/shared/Components/LikeButton.tsx

import React, { FC, useState } from 'react';
import { Button, Tooltip } from '@chakra-ui/react';

type LikeButtonProps = {
  /**
   * Опциональный идентификатор «цели» (пост или комментарий).
   * Нужен только для aria-label (или для отладки в DevTools).
   */
  targetId?: number | string;
  /**
   * Если true, кнопка изначально будет «лайкнута» (заполненное красное сердце).
   * По умолчанию — false (серое контурное сердце).
   */
  initialLiked?: boolean;
};

/**
 * Компонент «лайк» (сердечко). Используется обычный Chakra Button,
 * внутрь него вставляется «чистый» SVG без привлечения Icon/IconButton,
 * чтобы избежать ошибки «Element type is invalid... got: object».
 *
 * При клике меняет локальное состояние liked (true/false), без HTTP-запросов.
 */
const LikeButton: FC<LikeButtonProps> = ({ targetId, initialLiked = false }) => {
  const [liked, setLiked] = useState<boolean>(initialLiked);

  const toggleLike = () => {
    setLiked((prev) => !prev);
  };

  return (
    <Tooltip label={liked ? 'Убрать лайк' : 'Поставить лайк'} fontSize="sm">
      <Button
        aria-label={
          liked
            ? `Убрать лайк (${targetId})`
            : `Поставить лайк (${targetId})`
        }
        onClick={toggleLike}
        variant="ghost"
        size="sm"
        color={liked ? 'red.500' : 'gray.500'}
        p={0}
        _hover={{ bg: 'transparent' }}
      >
        {/* Вставляем «чистый» SVG для сердца */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          width="20"
          height="20"
          fill={liked ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5
                   2 5.42 4.42 3 7.5 3c1.74 0 3.41 0.81 4.5 2.09
                   C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5
                   c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
        </svg>
      </Button>
    </Tooltip>
  );
};

export default LikeButton;
