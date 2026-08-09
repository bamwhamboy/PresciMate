"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import type {
  AskResponse,
  ExplainResponse,
  ExtractedPrescription,
  HistoryRecord,
} from "@/lib/types";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { UploadArea } from "@/components/UploadArea";
import { LanguageSelect } from "@/components/LanguageSelect";
import { MedicineCard } from "@/components/MedicineCard";
import { InteractionWarning } from "@/components/InteractionWarning";
import { GroundingWarning } from "@/components/GroundingWarning";

const DISCLAIMER =
  "PresciMate explains what your doctor already prescribed. It does not diagnose or replace medical advice - always follow your doctor's or pharmacist's instructions. In an emergency, contact a doctor or local emergency services right away.";

type Step = "idle" | "reading" | "explaining" | "done" | "error";

export default function DashboardPage() {
  const { token, name, logout, loading: authLoading } = useAuth();
  const router = useRouter();

  const [tab, setTab] = useState<"upload" | "history">("upload");
  const [languages, setLanguages] = useState<string[]>(["English"]);
  const [language, setLanguage] = useState("English");

  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<Step>("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const [extracted, setExtracted] = useState<ExtractedPrescription | null>(null);
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<{ question: string; answer: AskResponse }[]>([]);
  const [asking, setAsking] = useState(false);

  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (!authLoading && !token) router.replace("/login");
  }, [authLoading, token, router]);

  useEffect(() => {
    api.getLanguages().then((res) => setLanguages(res.languages)).catch(() => {});
  }, []);

  useEffect(() => {
    if (tab === "history" && token) {
      setHistoryLoading(true);
      api
        .getHistory(token)
        .then(setHistory)
        .catch(() => {})
        .finally(() => setHistoryLoading(false));
    }
  }, [tab, token]);

  async function handleExplain() {
    if (!file || !token) return;
    setErrorMessage("");
    setResult(null);
    setChat([]);

    try {
      setStep("reading");
      setStatusMessage("Reading the prescription...");
      const extractedData = await api.extractPrescription(file, token);
      setExtracted(extractedData);

      if (!extractedData.medicines.length) {
        setErrorMessage("Couldn't find any medicines on this prescription. Try a clearer photo.");
        setStep("error");
        return;
      }

      setStep("explaining");
      setStatusMessage(`Writing your explanation in ${language}...`);
      const explainData = await api.explainPrescription(extractedData.medicines, language, token);
      setResult(explainData);
      setStep("done");
    } catch (e) {
      setErrorMessage(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
      setStep("error");
    }
  }

  async function handleAsk() {
    if (!question.trim() || !extracted || !token) return;
    setAsking(true);
    try {
      const answer = await api.askQuestion(question, extracted.medicines, language, token);
      setChat((prev) => [...prev, { question, answer }]);
      setQuestion("");
    } catch {
      // keep it simple - a failed follow-up question isn't critical path
    } finally {
      setAsking(false);
    }
  }

  async function handleDownloadPdf() {
    if (!result || !extracted || !token) return;
    setPdfLoading(true);
    try {
      const blob = await api.downloadPdf(extracted.medicines, result.explanation, language, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "prescription_explained.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setPdfLoading(false);
    }
  }

  if (authLoading || !token) return null;

  return (
    <div className="min-h-screen bg-paper">
      <header className="bg-white border-b border-mist">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="inline-block w-7 h-3.5 rounded-full bg-marigold relative" aria-hidden="true">
              <span className="absolute right-0 top-0 w-3.5 h-3.5 rounded-full bg-white" />
            </span>
            <span className="font-display font-semibold text-lg text-pharmacy-dark">PresciMate</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-ink/60 hidden sm:inline">Hi, {name}</span>
            <Button variant="ghost" onClick={logout} className="!py-1.5 !px-3 text-xs">
              Log out
            </Button>
          </div>
        </div>
      </header>

      <nav className="max-w-5xl mx-auto px-4 pt-4 flex gap-6 border-b border-mist">
        {(["upload", "history"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-3 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t ? "border-pharmacy text-pharmacy" : "border-transparent text-ink/50"
            }`}
          >
            {t === "upload" ? "Upload prescription" : "My history"}
          </button>
        ))}
      </nav>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {tab === "upload" ? (
          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <UploadArea onFileSelected={setFile} />
              <LanguageSelect languages={languages} value={language} onChange={setLanguage} />
              <Button
                onClick={handleExplain}
                disabled={!file || step === "reading" || step === "explaining"}
                className="w-full"
              >
                {step === "reading" || step === "explaining" ? statusMessage : "Explain my prescription"}
              </Button>
              {errorMessage && <p className="text-sm text-clay">{errorMessage}</p>}

              <Card className="!bg-marigold/5 !border-mist text-xs text-ink/70">
                {DISCLAIMER}
              </Card>
            </div>

            <div className="space-y-4">
              {extracted?.low_confidence && (
                <div className="bg-marigold/10 border-l-4 border-l-marigold rounded-md p-4 text-sm">
                  Handwriting was hard to read in places &mdash; please double check against the original.
                </div>
              )}

              {extracted && extracted.medicines.length > 0 && (
                <div className="space-y-3">
                  <h2 className="font-display font-semibold text-ink">Medicines found</h2>
                  {(result?.translated_medicines ?? extracted.medicines).map((m, i) => (
                    <MedicineCard key={i} medicine={m} />
                  ))}
                </div>
              )}

              {result && result.interactions.length > 0 && (
                <div className="space-y-3">
                  <h2 className="font-display font-semibold text-ink">Interaction warnings</h2>
                  {result.interactions.map((interaction, i) => (
                    <InteractionWarning key={i} interaction={interaction} />
                  ))}
                </div>
              )}

              {result && (
                <div className="space-y-3">
                  <h2 className="font-display font-semibold text-ink">Explained in {language}</h2>
                  <GroundingWarning grounding={result.grounding} />
                  <Card torn>
                    <div className="prose prose-sm max-w-none text-ink/90
                      prose-headings:font-display prose-headings:text-ink
                      prose-strong:text-ink prose-p:leading-relaxed">
                      <ReactMarkdown>{result.explanation}</ReactMarkdown>
                    </div>
                  </Card>
                  <Button variant="secondary" onClick={handleDownloadPdf} disabled={pdfLoading}>
                    {pdfLoading ? "Preparing PDF..." : "Download as PDF"}
                  </Button>
                </div>
              )}

              {result && (
                <div className="space-y-3">
                  <h2 className="font-display font-semibold text-ink">Ask a question</h2>
                  <div className="space-y-3">
                    {chat.map((entry, i) => (
                      <div key={i} className="space-y-1">
                        <p className="text-sm font-medium text-ink/70">{entry.question}</p>
                        <Card className="!p-3 text-sm">
                          {entry.answer.emergency && (
                            <p className="text-clay font-semibold mb-1">Please seek help immediately</p>
                          )}
                          <div className="prose prose-sm max-w-none prose-p:leading-relaxed">
                            <ReactMarkdown>{entry.answer.answer}</ReactMarkdown>
                          </div>
                          <GroundingWarning grounding={entry.answer.grounding} />
                        </Card>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                      placeholder="e.g. Can I take this with milk?"
                      className="flex-1 rounded-md border border-mist px-3 py-2 text-sm
                        focus:outline-none focus:ring-2 focus:ring-pharmacy"
                    />
                    <Button onClick={handleAsk} disabled={asking || !question.trim()}>
                      {asking ? "..." : "Ask"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="max-w-2xl space-y-3">
            <h2 className="font-display font-semibold text-ink text-lg">Your past prescriptions</h2>
            {historyLoading && <p className="text-sm text-ink/50">Loading...</p>}
            {!historyLoading && history.length === 0 && (
              <p className="text-sm text-ink/50">No prescriptions yet &mdash; upload one to get started.</p>
            )}
            {history.map((record) => (
              <Card key={record.prescription_id} torn>
                <p className="text-xs text-ink/50">{record.created_at.slice(0, 10)}</p>
                <p className="font-medium text-sm mt-1">{record.medicines}</p>
                <p className="text-sm text-ink/80 mt-2 whitespace-pre-line">{record.explanation}</p>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
