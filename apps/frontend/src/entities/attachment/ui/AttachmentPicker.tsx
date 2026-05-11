import React from 'react';
import {Button} from '@chakra-ui/react';
import {FaPaperclip} from 'react-icons/fa';
import {AttachmentTile} from './AttachmentGrid';
import styles from './AttachmentTile.module.css';

type Props = {
  files: File[];
  inputId: string;
  onChange: (files: File[]) => void;
};

export const AttachmentPicker = ({files, inputId, onChange}: Props) => {
  const handleFilesSelected = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files ?? []);
    onChange([...files, ...selectedFiles].slice(0, 5));
    event.target.value = '';
  };

  const handleRemove = (indexToRemove: number) => {
    onChange(files.filter((_file, index) => index !== indexToRemove));
  };

  return (
    <>
      <div className={styles.picker}>
        <input
          className={styles.input}
          id={inputId}
          multiple
          onChange={handleFilesSelected}
          type="file"
        />
        <Button asChild size="sm" variant="outline">
          <label htmlFor={inputId}>
            <FaPaperclip />
            Attach files
          </label>
        </Button>
      </div>
      {files.length ? (
        <div className={styles.grid}>
          {files.map((file, index) => (
            <AttachmentTile
              contentType={file.type}
              fileName={file.name}
              fileSize={file.size}
              key={`${file.name}-${file.lastModified}-${index}`}
              onRemove={() => handleRemove(index)}
            />
          ))}
        </div>
      ) : null}
    </>
  );
};
