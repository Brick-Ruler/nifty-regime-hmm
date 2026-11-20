// Netlify Serverless Function: Dynamic Portfolio Ledger API
// Always fetches the latest committed ledger from GitHub raw repository
// Ensures zero stale cache when users click the Netlify link in email briefings

const GITHUB_RAW_LEDGER = "https://raw.githubusercontent.com/Brick-Ruler/nifty-regime-hmm/main/portfolio_ledger.json";

export default async (req, context) => {
  try {
    const resp = await fetch(`${GITHUB_RAW_LEDGER}?_t=${Date.now()}`, {
      headers: {
        "User-Agent": "Netlify-Dynamic-Ledger/1.0",
        "Cache-Control": "no-cache, no-store, must-revalidate"
      }
    });

    if (resp.ok) {
      const ledger = await resp.json();
      return new Response(JSON.stringify(ledger), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate"
        }
      });
    }
  } catch (err) {
    console.warn("Failed to fetch GitHub raw ledger:", err);
  }

  // Fallback to local static file if GitHub raw is temporarily unreachable
  return new Response(JSON.stringify({ error: "Failed to fetch live ledger" }), {
    status: 502,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*"
    }
  });
};

export const config = {
  path: "/api/ledger"
};
