import { ChangeEvent, useRef } from "react";

type UploadButtonProps = {
  disabled?: boolean;
  maxUploadSizeMb: number;
  onSelect: (files: File[]) => void;
};

export default function UploadButton({ disabled, maxUploadSizeMb, onSelect }: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    if (files.length > 0) {
      onSelect(files);
    }
    event.target.value = "";
  };

  return (
    <>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        className="h-12 min-w-[58px] shrink-0 rounded-xl border border-slate-700 bg-slate-900 px-3.5 text-[11px] font-semibold text-slate-100 transition hover:border-slate-500 active:scale-95 touch-manipulation disabled:cursor-not-allowed disabled:opacity-50 sm:h-14 sm:min-w-[62px]"
        title={`PDF veya belge yukle (max ${maxUploadSizeMb} MB)`}
      >
        Yukle
      </button>
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp"
        onChange={onChange}
      />
    </>
  );
}
