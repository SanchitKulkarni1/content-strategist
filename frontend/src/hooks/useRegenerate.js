import { useCallback, useState } from "react";
import { regeneratePosts } from "../api/client";

export function useRegenerate() {
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState(null);

  const regenerate = useCallback(async (brandUrl, competitorUrls, selectedTrend) => {
    setIsRegenerating(true);
    setError(null);

    try {
      const data = await regeneratePosts(brandUrl, competitorUrls, selectedTrend);
      setPosts(Array.isArray(data.post_prompts) ? data.post_prompts : []);
      return data;
    } catch (err) {
      setError(err.message || "Failed to regenerate posts");
      throw err;
    } finally {
      setIsRegenerating(false);
    }
  }, []);

  return { regenerate, isRegenerating, posts, error };
}
