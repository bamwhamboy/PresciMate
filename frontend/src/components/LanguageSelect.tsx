interface LanguageSelectProps {
  languages: string[];
  value: string;
  onChange: (language: string) => void;
}

export function LanguageSelect({ languages, value, onChange }: LanguageSelectProps) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-ink/70">Explain my prescription in</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-mist bg-white px-3 py-2 text-sm
          focus:outline-none focus:ring-2 focus:ring-pharmacy"
      >
        {languages.map((lang) => (
          <option key={lang} value={lang}>
            {lang}
          </option>
        ))}
      </select>
    </label>
  );
}
