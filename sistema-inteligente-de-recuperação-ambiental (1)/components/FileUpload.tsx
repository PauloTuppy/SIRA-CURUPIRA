
import React, { useState, useCallback, useRef } from 'react';
import { UploadIcon } from './icons';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, disabled }) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (disabled) return;
    
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  }, [onFileSelect, disabled]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const containerClasses = `
    border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-300 cursor-pointer
    ${disabled ? 'bg-gray-200 border-gray-300 cursor-not-allowed' : 'border-brand-accent bg-brand-light/20 hover:bg-brand-light/40'}
    ${isDragging ? 'bg-brand-accent/30 border-brand-primary' : ''}
  `;

  return (
    <div
      className={containerClasses}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        onChange={handleFileChange}
        accept="image/*,video/*"
        disabled={disabled}
      />
      <div className="flex flex-col items-center justify-center space-y-4">
        <UploadIcon className={`h-12 w-12 ${disabled ? 'text-gray-400' : 'text-brand-secondary'}`} />
        <p className={`font-semibold ${disabled ? 'text-gray-500' : 'text-brand-primary'}`}>
          Arraste e solte uma imagem ou vídeo aqui
        </p>
        <p className={`text-sm ${disabled ? 'text-gray-400' : 'text-gray-600'}`}>
          ou <span className="text-brand-secondary font-bold">clique para selecionar</span>
        </p>
        <p className="text-xs text-gray-500 mt-2">Suporta PNG, JPG, GIF, MP4 de até 50MB</p>
      </div>
    </div>
  );
};

export default FileUpload;
