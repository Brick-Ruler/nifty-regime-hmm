// Netlify Universal Cloud Webhook Endpoint
// Serves at: /.netlify/functions/trigger_scan?mode=premarket | eod
// Can be pinged on-demand, tested via curl/browser, or hooked to external cloud cron services.

import { dispatchWorkflow } from "./gh_client.mjs";

export default async (req, context) => {
  const url = new URL(req.url);
  const mode = url.searchParams.get("mode") || "premarket";
  const workflow = mode === "eod" ? "eod_scan.yml" : "pre_market_scan.yml";
  const timestamp = new Date().toISOString();

  console.log(`[NETLIFY WEBHOOK] Received trigger request for ${mode} (${workflow}) at ${timestamp}`);

  try {
    const resp = await dispatchWorkflow(workflow);

    if (resp.status === 204) {
      return new Response(JSON.stringify({
        success: true,
        message: `Successfully triggered GitHub Actions workflow: ${workflow}`,
        mode,
        dispatched_at: timestamp
      }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*"
        }
      });
    } else {
      const errText = await resp.text();
      return new Response(JSON.stringify({
        success: false,
        error: `GitHub API error: ${resp.status}`,
        details: errText,
        dispatched_at: timestamp
      }), {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*"
        }
      });
    }
  } catch (err) {
    return new Response(JSON.stringify({
      success: false,
      error: err.message,
      dispatched_at: timestamp
    }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }
};
