import React, {ReactNode} from 'react';
import {Box} from '@chakra-ui/react';
import styles from './MarkdownRenderer.module.css';

type Block =
  | {
      type: 'paragraph';
      content: string;
    }
  | {
      type: 'code';
      content: string;
      language?: string;
    };

type Props = {
  content: string;
  emptyText?: string;
};

const SAFE_PROTOCOLS = new Set(['http:', 'https:', 'mailto:']);

const isSafeUrl = (url: string) => {
  const trimmedUrl = url.trim();

  if (
    (trimmedUrl.startsWith('/') && !trimmedUrl.startsWith('//')) ||
    trimmedUrl.startsWith('#')
  ) {
    return true;
  }

  try {
    const parsedUrl = new URL(trimmedUrl);
    return SAFE_PROTOCOLS.has(parsedUrl.protocol);
  } catch {
    return false;
  }
};

const splitTextByNewlines = (text: string, keyPrefix: string): ReactNode[] =>
  text.split('\n').flatMap((part, index, parts) => {
    const nodes: ReactNode[] = [part];

    if (index < parts.length - 1) {
      nodes.push(<br key={`${keyPrefix}-br-${index}`} />);
    }

    return nodes;
  });

const findNextSpecial = (text: string, start: number) => {
  const markers = ['`', '***', '**', '*', '[']
    .map(marker => text.indexOf(marker, start))
    .filter(index => index >= 0);

  return markers.length > 0 ? Math.min(...markers) : -1;
};

const parseInline = (text: string, keyPrefix = 'md'): ReactNode[] => {
  const nodes: ReactNode[] = [];
  let cursor = 0;

  while (cursor < text.length) {
    if (text.startsWith('`', cursor)) {
      const end = text.indexOf('`', cursor + 1);

      if (end > cursor + 1) {
        nodes.push(
          <code
            className={styles.inlineCode}
            key={`${keyPrefix}-code-${cursor}`}>
            {text.slice(cursor + 1, end)}
          </code>,
        );
        cursor = end + 1;
        continue;
      }
    }

    if (text.startsWith('***', cursor)) {
      const end = text.indexOf('***', cursor + 3);

      if (end > cursor + 3) {
        nodes.push(
          <strong key={`${keyPrefix}-strong-em-${cursor}`}>
            <em>
              {parseInline(
                text.slice(cursor + 3, end),
                `${keyPrefix}-strong-em`,
              )}
            </em>
          </strong>,
        );
        cursor = end + 3;
        continue;
      }
    }

    if (text.startsWith('**', cursor)) {
      const end = text.indexOf('**', cursor + 2);

      if (end > cursor + 2) {
        nodes.push(
          <strong key={`${keyPrefix}-strong-${cursor}`}>
            {parseInline(text.slice(cursor + 2, end), `${keyPrefix}-strong`)}
          </strong>,
        );
        cursor = end + 2;
        continue;
      }
    }

    if (text.startsWith('*', cursor) && !text.startsWith('**', cursor)) {
      const end = text.indexOf('*', cursor + 1);

      if (end > cursor + 1 && !text.startsWith('*', end + 1)) {
        nodes.push(
          <em key={`${keyPrefix}-em-${cursor}`}>
            {parseInline(text.slice(cursor + 1, end), `${keyPrefix}-em`)}
          </em>,
        );
        cursor = end + 1;
        continue;
      }
    }

    if (text.startsWith('[', cursor)) {
      const textEnd = text.indexOf('](', cursor + 1);
      const urlEnd = textEnd >= 0 ? text.indexOf(')', textEnd + 2) : -1;

      if (textEnd > cursor + 1 && urlEnd > textEnd + 2) {
        const label = text.slice(cursor + 1, textEnd);
        const href = text.slice(textEnd + 2, urlEnd).trim();

        if (isSafeUrl(href)) {
          nodes.push(
            <a
              href={href}
              key={`${keyPrefix}-link-${cursor}`}
              rel="noopener noreferrer"
              target={href.startsWith('http') ? '_blank' : undefined}>
              {parseInline(label, `${keyPrefix}-link`)}
            </a>,
          );
          cursor = urlEnd + 1;
          continue;
        }
      }
    }

    const nextSpecial = findNextSpecial(text, cursor + 1);
    const textEnd = nextSpecial >= 0 ? nextSpecial : text.length;
    nodes.push(
      ...splitTextByNewlines(
        text.slice(cursor, textEnd),
        `${keyPrefix}-${cursor}`,
      ),
    );
    cursor = textEnd;
  }

  return nodes;
};

const parseBlocks = (content: string): Block[] => {
  const lines = content.replace(/\r\n?/g, '\n').split('\n');
  const blocks: Block[] = [];
  let cursor = 0;

  while (cursor < lines.length) {
    const line = lines[cursor];

    if (!line.trim()) {
      cursor += 1;
      continue;
    }

    if (line.trimStart().startsWith('```')) {
      const language = line.trim().slice(3).trim() || undefined;
      const codeLines: string[] = [];
      cursor += 1;

      while (
        cursor < lines.length &&
        !lines[cursor].trimStart().startsWith('```')
      ) {
        codeLines.push(lines[cursor]);
        cursor += 1;
      }

      if (cursor < lines.length) {
        cursor += 1;
      }

      blocks.push({
        type: 'code',
        content: codeLines.join('\n'),
        language,
      });
      continue;
    }

    const paragraphLines = [line];
    cursor += 1;

    while (
      cursor < lines.length &&
      lines[cursor].trim() &&
      !lines[cursor].trimStart().startsWith('```')
    ) {
      paragraphLines.push(lines[cursor]);
      cursor += 1;
    }

    blocks.push({
      type: 'paragraph',
      content: paragraphLines.join('\n'),
    });
  }

  return blocks;
};

export const MarkdownRenderer = ({
  content,
  emptyText = 'Nothing to preview yet',
}: Props) => {
  const blocks = parseBlocks(content);

  if (blocks.length === 0) {
    return <Box className={styles.emptyPreview}>{emptyText}</Box>;
  }

  return (
    <Box className={styles.markdown}>
      {blocks.map((block, index) => {
        if (block.type === 'code') {
          return (
            <pre className={styles.codeBlock} key={`block-${index}`}>
              {block.language ? (
                <span className={styles.codeLanguage}>{block.language}</span>
              ) : null}
              <code>{block.content}</code>
            </pre>
          );
        }

        return (
          <p key={`block-${index}`}>
            {parseInline(block.content, `block-${index}`)}
          </p>
        );
      })}
    </Box>
  );
};
