"use client";

import { useRef, useState, type ChangeEvent } from "react";

interface UploadAreaProps {
  onFileSelected: (file: File) => void;
}

export function UploadArea({ onFileSelected }: UploadAreaProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreviewUrl(URL.createObjectURL(file));
    onFileSelected(file);
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={handleChange}
        className="hidden"
        id="prescription-upload"
      />
      {previewUrl ? (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="block w-full rounded-lg overflow-hidden border border-mist"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={previewUrl} alt="Your uploaded prescription" className="w-full h-auto" />
        </button>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="w-full aspect-[4/3] rounded-lg border-2 border-dashed border-mist-dark
            flex flex-col items-center justify-center gap-2 text-ink/60 hover:border-pharmacy
            hover:text-pharmacy transition-colors"
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14M14 8h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="text-sm font-medium">Take or upload a photo of your prescription</span>
        </button>
      )}
    </div>
  );
}
