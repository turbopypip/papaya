import React from 'react';
import {Attachment} from '@/entities/attachment/attachement';
import styles from './AttachmentTile.module.css';

type AttachmentKind = {
  color: string;
  label: string;
  isImage: boolean;
};

const filePalette: Record<string, AttachmentKind> = {
  pdf: {color: '#d93636', label: 'PDF', isImage: false},
  xls: {color: '#178a4b', label: 'XLS', isImage: false},
  xlsx: {color: '#178a4b', label: 'XLSX', isImage: false},
  csv: {color: '#178a4b', label: 'CSV', isImage: false},
  doc: {color: '#2f6fce', label: 'DOC', isImage: false},
  docx: {color: '#2f6fce', label: 'DOCX', isImage: false},
  ppt: {color: '#d86b24', label: 'PPT', isImage: false},
  pptx: {color: '#d86b24', label: 'PPTX', isImage: false},
  ipynb: {color: '#6f4bd8', label: 'IPYNB', isImage: false},
  jpg: {color: '#1f8a8a', label: 'IMG', isImage: true},
  jpeg: {color: '#1f8a8a', label: 'IMG', isImage: true},
  png: {color: '#1f8a8a', label: 'IMG', isImage: true},
  gif: {color: '#1f8a8a', label: 'GIF', isImage: true},
  webp: {color: '#1f8a8a', label: 'IMG', isImage: true},
  txt: {color: '#667085', label: 'TXT', isImage: false},
  zip: {color: '#7a4cc2', label: 'ZIP', isImage: false},
};

const getExtension = (name: string) => {
  const extension = name.split('.').pop()?.toLowerCase();
  return extension && extension !== name.toLowerCase() ? extension : '';
};

const getKind = (fileName: string, contentType?: string): AttachmentKind => {
  const extension = getExtension(fileName);
  if (extension && filePalette[extension]) {
    return filePalette[extension];
  }
  if (contentType?.startsWith('image/')) {
    return {color: '#1f8a8a', label: 'IMG', isImage: true};
  }
  if (contentType === 'application/x-ipynb+json') {
    return filePalette.ipynb;
  }

  return {color: '#475467', label: extension?.toUpperCase() || 'FILE', isImage: false};
};

const formatFileSize = (size?: number) => {
  if (!size) {
    return '';
  }

  if (size < 1024 * 1024) {
    return `${Math.ceil(size / 1024)} KB`;
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`;
};

const shouldOpenInBrowser = (fileName: string, contentType?: string) => {
  const extension = getExtension(fileName);
  return (
    contentType?.startsWith('image/') ||
    contentType === 'application/pdf' ||
    ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'].includes(extension)
  );
};

type TileProps = {
  fileName: string;
  contentType?: string;
  fileSize?: number;
  url?: string;
  onRemove?: () => void;
};

export const AttachmentTile = ({
  fileName,
  contentType,
  fileSize,
  url,
  onRemove,
}: TileProps) => {
  const kind = getKind(fileName, contentType);
  const formattedSize = formatFileSize(fileSize);
  const openInBrowser = shouldOpenInBrowser(fileName, contentType);
  const style = {
    '--attachment-color': kind.color,
    '--attachment-preview': url ? `url(${url})` : undefined,
  } as React.CSSProperties;
  const className = `${styles.tile} ${kind.isImage && url ? styles.imageTile : ''}`;
  const content = (
    <>
      <span className={styles.type}>{kind.label}</span>
      <span className={styles.details}>
        <span className={styles.name}>{fileName}</span>
        {formattedSize ? <span className={styles.size}>{formattedSize}</span> : null}
      </span>
      {onRemove ? (
        <button
          aria-label={`Remove ${fileName}`}
          className={styles.remove}
          onClick={event => {
            event.preventDefault();
            onRemove();
          }}
          type="button">
          ×
        </button>
      ) : null}
    </>
  );

  if (url) {
    return (
      <a
        className={className}
        download={openInBrowser ? undefined : fileName}
        href={url}
        rel="noreferrer"
        style={style}
        target={openInBrowser ? '_blank' : undefined}
        title={formattedSize ? `${fileName} (${formattedSize})` : fileName}>
        {content}
      </a>
    );
  }

  return (
    <button className={className} style={style} type="button">
      {content}
    </button>
  );
};

export const AttachmentGrid = ({
  attachments,
}: {
  attachments?: Attachment[];
}) => {
  if (!attachments?.length) {
    return null;
  }

  return (
    <div className={styles.grid}>
      {attachments.map(attachment => (
        <AttachmentTile
          contentType={attachment.content_type}
          fileName={attachment.file_name}
          fileSize={attachment.size}
          key={attachment.ID}
          url={attachment.url}
        />
      ))}
    </div>
  );
};
