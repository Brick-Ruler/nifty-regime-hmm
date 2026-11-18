// Netlify Serverless Function: Real-Time NSE Quotes API
// Runs server-side in Node.js runtime (Zero CORS issues!)

const SYMBOLS = [
  '^NSEI', '^INDIAVIX',
  // 8 Aggressive Champions (Option B Top-5 Sector Rotation)
  'PERSISTENT.NS', 'COFORGE.NS', 'CHOLAFIN.NS', 'FEDERALBNK.NS',
  'INDHOTEL.NS', 'EIHOTEL.NS', 'BALKRISIND.NS', 'DIXON.NS',
  // 8 Distinct Defensive Fortresses
  'COLPAL.NS', 'GLAXO.NS', 'MARICO.NS', 'TORNTPHARM.NS',
  'KANSAINER.NS', 'MGL.NS', 'COROMANDEL.NS', 'PETRONET.NS'
];

async function fetchYahooQuote(symbol) {
  try {
    const encoded = encodeURIComponent(symbol);
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encoded}?range=1d&interval=5m`;
    const resp = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' },
      signal: AbortSignal.timeout(4000)
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    const meta = data?.chart?.result?.[0]?.meta;
    if (!meta) return null;

    const cmp = meta.regularMarketPrice;
    const prev = meta.chartPreviousClose || meta.previousClose;
    if (cmp != null && prev != null) {
      const chg = ((cmp - prev) / prev) * 100.0;
      return {
        cmp: Math.round(cmp * 100) / 100,
        prev_close: Math.round(prev * 100) / 100,
        change_pct: Math.round(chg * 100) / 100
      };
    }
  } catch (err) {
    // Return null on timeout / error
  }
  return null;
}

export default async (req, context) => {
  const startTime = Date.now();
  
  // Fetch all symbols concurrently using Promise.all
  const results = await Promise.all(
    SYMBOLS.map(async (s) => ({ symbol: s, data: await fetchYahooQuote(s) }))
  );

  const quotes = {
    timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
    source: 'NETLIFY_SERVERLESS_REALTIME_FEED',
    latency_ms: Date.now() - startTime,
    stocks: {}
  };

  for (const r of results) {
    if (!r.data) continue;
    if (r.symbol === '^NSEI') quotes.nifty = r.data;
    else if (r.symbol === '^INDIAVIX') quotes.vix = r.data;
    else quotes.stocks[r.symbol] = r.data;
  }

  return new Response(JSON.stringify(quotes), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate'
    }
  });
};

export const config = {
  path: "/api/quotes"
};
