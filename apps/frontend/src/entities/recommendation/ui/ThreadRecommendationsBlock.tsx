'use client';

import React, {KeyboardEvent, useEffect, useMemo, useRef, useState} from 'react';
import {Box, Flex, Text} from '@chakra-ui/react';
import {useRouter} from 'next/navigation';
import {ArrowRight, Sparkles} from 'lucide-react';
import {StatePanel} from '@/shared/Components/StatePanel';
import {Tag} from '@/shared/Components/Tag/ui/tag';
import {useThreadRecommendations} from '@/entities/recommendation/queries/useThreadRecommendations';
import {recordRecommendationEvent} from '@/entities/recommendation/api/recordRecommendationEvent';
import {ThreadRecommendation} from '@/entities/recommendation';

type ThreadRecommendationsBlockProps = {
  title: string;
  placement: string;
  enabled?: boolean;
  limit?: number;
  excludeThreadId?: string;
};

export const ThreadRecommendationsBlock = ({
  title,
  placement,
  enabled = true,
  limit = 5,
  excludeThreadId,
}: ThreadRecommendationsBlockProps) => {
  const router = useRouter();
  const blockRef = useRef<HTMLDivElement | null>(null);
  const impressionKeysRef = useRef<Set<string>>(new Set());
  const [isActuallyShown, setIsActuallyShown] = useState(false);
  const queryLimit = excludeThreadId ? limit + 1 : limit;
  const {recommendations, status, loaded, error} = useThreadRecommendations(
    queryLimit,
    enabled,
  );

  const visibleRecommendations = useMemo(
    () =>
      recommendations
        .filter(recommendation => recommendation.thread.ID !== excludeThreadId)
        .slice(0, limit),
    [excludeThreadId, limit, recommendations],
  );

  useEffect(() => {
    if (loaded || error || visibleRecommendations.length === 0) {
      setIsActuallyShown(false);
      return;
    }

    const target = blockRef.current;
    if (!target || typeof IntersectionObserver === 'undefined') {
      setIsActuallyShown(true);
      return;
    }

    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]?.isIntersecting) {
          setIsActuallyShown(true);
          observer.disconnect();
        }
      },
      {threshold: 0.25},
    );

    observer.observe(target);

    return () => observer.disconnect();
  }, [error, loaded, visibleRecommendations.length]);

  useEffect(() => {
    if (
      !enabled ||
      !isActuallyShown ||
      loaded ||
      error ||
      visibleRecommendations.length === 0
    ) {
      return;
    }

    visibleRecommendations.forEach((recommendation, index) => {
      const key = eventKey(recommendation, placement, index + 1);
      if (impressionKeysRef.current.has(key)) {
        return;
      }

      impressionKeysRef.current.add(key);
      void recordRecommendationEvent({
        event_type: 'recommendation_impression',
        thread_id: recommendation.thread.ID,
        model_version: recommendation.model_version,
        position: index + 1,
        recommendation_source: recommendation.recommendation_source,
        placement,
        run_id: recommendation.run_id,
        generation_id: recommendation.generation_id,
      }).catch(() => {
        impressionKeysRef.current.delete(key);
      });
    });
  }, [enabled, error, isActuallyShown, loaded, placement, visibleRecommendations]);

  const openRecommendation = async (
    recommendation: ThreadRecommendation,
    position: number,
  ) => {
    await recordRecommendationEvent({
      event_type: 'recommendation_clicked',
      thread_id: recommendation.thread.ID,
      model_version: recommendation.model_version,
      position,
      recommendation_source: recommendation.recommendation_source,
      placement,
      run_id: recommendation.run_id,
      generation_id: recommendation.generation_id,
    }).catch(() => undefined);
    router.push(`/thread/${recommendation.thread.ID}`);
  };

  const handleKeyDown = (
    event: KeyboardEvent<HTMLDivElement>,
    recommendation: ThreadRecommendation,
    position: number,
  ) => {
    if (event.key !== 'Enter' && event.key !== ' ') {
      return;
    }

    event.preventDefault();
    void openRecommendation(recommendation, position);
  };

  if (!enabled) {
    return null;
  }

  if (loaded) {
    return (
      <Box marginBottom="1.5rem">
        <StatePanel title="Загружаем рекомендации">
          Модель подбирает треды для вас.
        </StatePanel>
      </Box>
    );
  }

  if (error) {
    return (
      <Box marginBottom="1.5rem">
        <StatePanel title="Не удалось загрузить рекомендации" tone="danger">
          {error}
        </StatePanel>
      </Box>
    );
  }

  if (visibleRecommendations.length === 0) {
    return (
      <Box marginBottom="1.5rem">
        <StatePanel title="Пока нет рекомендаций модели">
          {status === 'model_not_ready'
            ? 'Модель еще не обучена или выдача пока не сгенерирована.'
            : 'Пока недостаточно статистики, чтобы уверенно подобрать треды.'}
        </StatePanel>
      </Box>
    );
  }

  return (
    <Box ref={blockRef} marginBottom="1.5rem">
      <Flex align="center" gap="2" marginBottom="0.75rem">
        <Sparkles size={18} />
        <Text fontWeight="700" fontSize="lg">
          {title}
        </Text>
      </Flex>
      <Flex direction="column" gap="2">
        {visibleRecommendations.map((recommendation, index) => (
          <Box
            key={`${recommendation.thread.ID}-${recommendation.run_id}`}
            role="button"
            tabIndex={0}
            cursor="pointer"
            borderWidth="1px"
            borderColor="gray.200"
            borderRadius="8px"
            padding="0.85rem"
            bg="white"
            _hover={{borderColor: 'gray.300', bg: 'gray.50'}}
            onClick={() => void openRecommendation(recommendation, index + 1)}
            onKeyDown={event =>
              handleKeyDown(event, recommendation, index + 1)
            }>
            <Flex align="flex-start" justify="space-between" gap="3">
              <Box minWidth="0">
                <Text
                  fontWeight="600"
                  whiteSpace="pre-wrap"
                  overflowWrap="anywhere">
                  {recommendation.thread.title}
                </Text>
                <Text color="gray.600" fontSize="sm" marginTop="0.25rem">
                  @{recommendation.thread.author?.username ?? 'неизвестно'}
                </Text>
              </Box>
              <Box color="gray.500" paddingTop="0.1rem">
                <ArrowRight size={18} />
              </Box>
            </Flex>
            {recommendation.thread.categories?.length ? (
              <Flex gap="2" wrap="wrap" marginTop="0.65rem">
                {recommendation.thread.categories.map(category => (
                  <Tag key={category} colorScheme="purple">
                    {category}
                  </Tag>
                ))}
              </Flex>
            ) : null}
            {recommendation.model_version ? (
              <Text color="gray.500" fontSize="xs" marginTop="0.65rem">
                {recommendation.model_version} - score{' '}
                {recommendation.score.toFixed(3)}
              </Text>
            ) : null}
          </Box>
        ))}
      </Flex>
    </Box>
  );
};

function eventKey(
  recommendation: ThreadRecommendation,
  placement: string,
  position: number,
) {
  return [
    placement,
    recommendation.thread.ID,
    recommendation.model_version,
    recommendation.run_id,
    recommendation.generation_id,
    position,
  ].join(':');
}
