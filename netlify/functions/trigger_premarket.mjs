// Autonomous Cloud Trigger: Pre-Market Scan (08:50 AM IST / 03:20 UTC Mon-Fri)
// Runs on AWS Lambda in Netlify Cloud 24/7/365 independent of local laptop

import { dispatchWorkflow } from "./gh_client.mjs";

export default async (req, context) => {
  const timestamp = new Date().toISOString();
  console.log(`[NETLIFY CLOUD SCHEDULER] Firing Pre-Market Scan at ${timestamp}`);
  
  try {
    const resp = await dispatchWorkflow("pre_market_scan.yml");

    if (resp.status === 204) {
      console.log("[NETLIFY CLOUD SCHEDULER] Successfully dispatched pre_market_scan.yml to GitHub Actions!");
      return new Response(JSON.stringify({ success: true, scan: "premarket", status: 204, timestamp }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    } else {
      const errText = await resp.text();
      console.error(`[NETLIFY CLOUD SCHEDULER] Failed with status ${resp.status}:`, errText);
      return new Response(JSON.stringify({ success: false, status: resp.status, error: errText, timestamp }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  } catch (err) {
    console.error("[NETLIFY CLOUD SCHEDULER] Network error:", err);
    return new Response(JSON.stringify({ success: false, error: err.message, timestamp }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
};
