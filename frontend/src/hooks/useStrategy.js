import { useCallback, useState } from "react";
import { generateStrategy, streamStrategy } from "../api/client";

const INITIAL_PROGRESS = {
  stage: "idle",
  message: "Waiting to start",
  percent: 0,
};

export function useStrategy() {
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(INITIAL_PROGRESS);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const run = useCallback(async (brandUrl, competitorUrls) => {
    setIsRunning(true);
    setError(null);
    setProgress({ stage: "scraping", message: "Starting pipeline...", percent: 5 });

    const hasSSE = typeof window !== "undefined" && typeof window.EventSource !== "undefined";
    const canUseSSE = hasSSE && navigator.onLine;

    if (!canUseSSE) {
      try {
        setProgress({ stage: "scraping", message: "Scraping Instagram profiles...", percent: 20 });
        const data = await generateStrategy(brandUrl, competitorUrls);
        setResults(data);
        setProgress({ stage: "complete", message: "Complete", percent: 100 });
        return data;
      } catch (err) {
        setError(err.message || "Failed to generate strategy");
        throw err;
      } finally {
        setIsRunning(false);
      }
    }

    return new Promise((resolve, reject) => {
      let cleanup = () => {};

      try {
        cleanup = streamStrategy(brandUrl, competitorUrls, (event) => {
          if (event.stage === "complete") {
            setResults(event.payload);
            setProgress({ stage: "complete", message: "Complete", percent: 100 });
            setIsRunning(false);
            cleanup();
            resolve(event.payload);
            return;
          }

          if (event.stage === "error") {
            const nextError = event.message || "Pipeline failed";
            setError(nextError);
            setIsRunning(false);
            cleanup();
            reject(new Error(nextError));
            return;
          }

          setProgress({
            stage: event.stage || "running",
            message: event.message || "Running",
            percent: Number(event.progress || 0),
          });
        });
      } catch (err) {
        setError(err.message || "Failed to connect stream");
        setIsRunning(false);
        reject(err);
      }
    });
  }, []);

  return { run, isRunning, progress, results, error };
}
