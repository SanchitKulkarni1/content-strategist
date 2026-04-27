const BASE = "http://localhost:8000/api";

export async function generateStrategy(brandUrl, competitorUrls) {
  const res = await fetch(`${BASE}/strategy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brand_url: brandUrl, competitor_urls: competitorUrls }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

export async function regeneratePosts(brandUrl, competitorUrls, selectedTrend) {
  const res = await fetch(`${BASE}/strategy/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      brand_url: brandUrl,
      competitor_urls: competitorUrls,
      selected_trend: selectedTrend,
    }),
  });

  if (!res.ok) {
    throw new Error(await res.text());
  }

  return res.json();
}

export function streamStrategy(brandUrl, competitorUrls, onEvent) {
  const params = new URLSearchParams({
    brand_url: brandUrl,
    competitor_urls: competitorUrls.join(","),
  });

  const es = new EventSource(`${BASE}/strategy/stream?${params.toString()}`);
  es.onmessage = (event) => onEvent(JSON.parse(event.data));
  es.onerror = () => es.close();

  return () => es.close();
}
