'use client';

import React, {useRef, useState} from 'react';
import {Box, Button, Flex, IconButton, Textarea} from '@chakra-ui/react';
import {
  Bold,
  Code,
  FileCode2,
  Italic,
  Link as LinkIcon,
  PencilLine,
  Eye,
} from 'lucide-react';
import {MarkdownRenderer} from './MarkdownRenderer';

type Props = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minH?: string;
  disabled?: boolean;
};

type FormatAction = {
  label: string;
  before: string;
  after: string;
  placeholder: string;
  icon: React.ReactNode;
};

const FORMAT_ACTIONS: FormatAction[] = [
  {
    label: 'Жирный',
    before: '**',
    after: '**',
    placeholder: 'жирный текст',
    icon: <Bold size={16} />,
  },
  {
    label: 'Курсив',
    before: '*',
    after: '*',
    placeholder: 'текст курсивом',
    icon: <Italic size={16} />,
  },
  {
    label: 'Ссылка',
    before: '[',
    after: '](https://example.com)',
    placeholder: 'текст ссылки',
    icon: <LinkIcon size={16} />,
  },
  {
    label: 'Код в строке',
    before: '`',
    after: '`',
    placeholder: 'код',
    icon: <Code size={16} />,
  },
  {
    label: 'Блок кода',
    before: '```\n',
    after: '\n```',
    placeholder: 'код',
    icon: <FileCode2 size={16} />,
  },
];

export const MarkdownEditor = ({
  value,
  onChange,
  placeholder,
  minH = '180px',
  disabled = false,
}: Props) => {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const applyFormat = ({
    before,
    after,
    placeholder: fallback,
  }: FormatAction) => {
    const textarea = textareaRef.current;

    if (!textarea) {
      onChange(`${value}${before}${fallback}${after}`);
      setPreviewOpen(false);
      return;
    }

    const selectionStart = textarea.selectionStart;
    const selectionEnd = textarea.selectionEnd;
    const selectedText = value.slice(selectionStart, selectionEnd);
    const hasSelection = selectionStart !== selectionEnd;
    const insertedText = `${before}${hasSelection ? selectedText : fallback}${after}`;
    const nextValue =
      value.slice(0, selectionStart) + insertedText + value.slice(selectionEnd);
    const nextSelectionStart = selectionStart + before.length;
    const nextSelectionEnd =
      nextSelectionStart +
      (hasSelection ? selectedText.length : fallback.length);

    onChange(nextValue);
    window.requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(nextSelectionStart, nextSelectionEnd);
    });
  };

  return (
    <Box>
      <Flex align="center" gap="2" justify="space-between" mb="2" wrap="wrap">
        <Flex gap="1" wrap="wrap">
          {FORMAT_ACTIONS.map(action => (
            <IconButton
              aria-label={action.label}
              disabled={disabled}
              key={action.label}
              onClick={() => applyFormat(action)}
              size="sm"
              type="button"
              variant="outline">
              {action.icon}
            </IconButton>
          ))}
        </Flex>
        <Flex gap="1">
          <Button
            disabled={disabled}
            onClick={() => setPreviewOpen(false)}
            size="sm"
            type="button"
            variant={previewOpen ? 'outline' : 'solid'}>
            <PencilLine size={16} />
            Писать
          </Button>
          <Button
            disabled={disabled}
            onClick={() => setPreviewOpen(true)}
            size="sm"
            type="button"
            variant={previewOpen ? 'solid' : 'outline'}>
            <Eye size={16} />
            Предпросмотр
          </Button>
        </Flex>
      </Flex>

      {previewOpen ? (
        <Box
          border="1px solid"
          borderColor="gray.200"
          borderRadius="6px"
          minH={minH}
          p="3">
          <MarkdownRenderer content={value} />
        </Box>
      ) : (
        <Textarea
          disabled={disabled}
          minH={minH}
          placeholder={placeholder}
          ref={textareaRef}
          value={value}
          onChange={event => onChange(event.target.value)}
        />
      )}
    </Box>
  );
};
