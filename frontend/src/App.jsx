import { useMemo, useState } from "react";
import FeatureCards from "./components/landing/FeatureCards";
import Hero from "./components/landing/Hero";
import HowItWorks from "./components/landing/HowItWorks";
import InputForm from "./components/landing/InputForm";
import SuccessBanner from "./components/results/SuccessBanner";
import TabNav from "./components/results/TabNav";
import TopBar from "./components/results/TopBar";
import CouncilorNotes from "./components/results/tabs/CouncilorNotes";
import GapAnalysis from "./components/results/tabs/GapAnalysis";
import PostPrompts from "./components/results/tabs/PostPrompts";
import StrategicReport from "./components/results/tabs/StrategicReport";
import ProgressStepper from "./components/shared/ProgressStepper";
import { useRegenerate } from "./hooks/useRegenerate";
import { useStrategy } from "./hooks/useStrategy";

export default function App() {
  const [view, setView] = useState("landing");
  const [brandUrl, setBrandUrl] = useState("");
  const [competitorUrls, setCompetitorUrls] = useState([]);
  const [results, setResults] = useState(null);
  const [linksLocked, setLinksLocked] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [activeTrend, setActiveTrend] = useState(null);
  const [regeneratingTrend, setRegeneratingTrend] = useState(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const {
    run,
    isRunning,
    progress,
    error: strategyError,
  } = useStrategy();

  const {
    regenerate,
    isRegenerating,
    posts: regeneratedPosts,
    error: regenerateError,
  } = useRegenerate();

  const currentPosts = useMemo(() => {
    if (regeneratedPosts.length > 0) return regeneratedPosts;
    return Array.isArray(results?.post_prompts) ? results.post_prompts : [];
  }, [regeneratedPosts, results]);

  const marketTrends = Array.isArray(results?.market_trends) ? results.market_trends : [];

  const runPipeline = async () => {
    setView("running");
    setBannerDismissed(false);

    try {
      const response = await run(brandUrl, competitorUrls);
      setResults(response);
      setActiveTrend(response.market_trends?.[0] || null);
      setView("results");
    } catch {
      setView("landing");
    }
  };

  const rerunPipeline = async () => {
    await runPipeline();
  };

  const resetToLanding = () => {
    setView("landing");
    setLinksLocked(false);
    setActiveTab(0);
    setBannerDismissed(false);
  };

  const handleRegenerate = async (trend) => {
    if (!trend) return;

    setActiveTrend(trend);
    setRegeneratingTrend(trend);
    try {
      const response = await regenerate(brandUrl, competitorUrls, trend);
      setResults((prev) => {
        if (!prev) return prev;
        return { ...prev, post_prompts: response.post_prompts || prev.post_prompts };
      });
    } catch {
      // Error is surfaced via hook state.
    } finally {
      setRegeneratingTrend(null);
    }
  };

  if (view === "running") {
    return <ProgressStepper progress={progress} />;
  }

  if (view === "results" && results) {
    return (
      <div className="min-h-screen px-6 pb-12 pt-20">
        <TopBar
          brandUrl={brandUrl}
          competitorUrls={competitorUrls}
          onEdit={resetToLanding}
          onRerun={rerunPipeline}
          isRunning={isRunning}
        />

        <main className="mx-auto mt-4 max-w-7xl space-y-4">
          <SuccessBanner dismissed={bannerDismissed} onDismiss={() => setBannerDismissed(true)} />
          <TabNav activeTab={activeTab} onTabChange={setActiveTab} />

          {activeTab === 0 ? <StrategicReport data={results.strategic_report} /> : null}
          {activeTab === 1 ? <GapAnalysis data={results.gap_analysis} /> : null}
          {activeTab === 2 ? (
            <PostPrompts
              data={currentPosts}
              trends={marketTrends}
              activeTrend={activeTrend}
              onTrendSelect={setActiveTrend}
              onRegenerate={handleRegenerate}
              isRegenerating={isRegenerating}
              regeneratingTrend={regeneratingTrend}
            />
          ) : null}
          {activeTab === 3 ? <CouncilorNotes data={results.councilor_notes} /> : null}

          {(strategyError || regenerateError) && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              {strategyError || regenerateError}
            </div>
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Hero />
      <FeatureCards />
      <HowItWorks />
      <InputForm
        brandUrl={brandUrl}
        competitorUrls={competitorUrls}
        linksLocked={linksLocked}
        isRunning={isRunning}
        onBrandUrlChange={setBrandUrl}
        onCompetitorUrlsChange={setCompetitorUrls}
        onLock={() => setLinksLocked(true)}
        onUnlock={() => setLinksLocked(false)}
        onRun={runPipeline}
      />
      {strategyError ? (
        <div className="mx-auto mb-8 w-full max-w-xl rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
          {strategyError}
        </div>
      ) : null}
    </div>
  );
}
