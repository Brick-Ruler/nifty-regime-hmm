// Autonomous Cloud Trigger: Sunday Night Macro Sentinel (09:30 PM IST / 16:00 UTC Sunday)
// Runs on AWS Lambda in Netlify Cloud 24/7/365 independent of local laptop

import { dispatchWorkflow } from "./gh_client.mjs";

export default async (req, context) => {
  const timestamp = new Date().toISOString();
  console.log(`[NETLIFY CLOUD SCHEDULER] Firing Sunday Night Macro Sentinel at ${timestamp}`);

  try {
    const resp = await dispatchWorkflow("sunday_sentinel.yml");

    if (resp.status === 204) {
      return new Response(JSON.stringify({ success: true, scan: "sunday_sentinel", status: 204, timestamp }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    } else {
      const errText = await resp.text();
      return new Response(JSON.stringify({ success: false, status: resp.status, error: errText, timestamp }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  } catch (err) {
    return new Response(JSON.stringify({ success: false, error: err.message, timestamp }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
};
