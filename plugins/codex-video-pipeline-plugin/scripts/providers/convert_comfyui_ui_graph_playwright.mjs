#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (!current.startsWith("--")) {
      continue;
    }
    const key = current.slice(2);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      parsed[key] = true;
      continue;
    }
    parsed[key] = value;
    index += 1;
  }
  return parsed;
}

async function loadPlaywright() {
  const candidates = [];
  if (process.env.PLAYWRIGHT_NODE_MODULES_DIR) {
    candidates.push(path.join(process.env.PLAYWRIGHT_NODE_MODULES_DIR, "playwright"));
  }
  candidates.push("playwright");
  let lastError = null;
  for (const candidate of candidates) {
    try {
      if (candidate === "playwright") {
        return await import("playwright");
      }
      return require(candidate);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError ?? new Error("playwright is not available");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const workflowPath = args.workflow;
  const outputPath = args.output;
  const baseUrl = String(args.url || "http://127.0.0.1:8188").replace(/\/+$/, "");
  if (!workflowPath || !outputPath) {
    throw new Error("Usage: convert_comfyui_ui_graph_playwright.mjs --workflow <workflow.json> --output <converted.json> [--url http://127.0.0.1:8188]");
  }
  const workflow = JSON.parse(await fs.readFile(workflowPath, "utf8"));
  const playwright = await loadPlaywright();
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(
      () => Boolean(globalThis.app?.loadGraphData) && Boolean(globalThis.app?.graphToPrompt),
      undefined,
      { timeout: 60000 },
    );
    const converted = await page.evaluate(async (graph) => {
      const app = globalThis.app;
      if (!app?.loadGraphData || !app?.graphToPrompt) {
        throw new Error("ComfyUI frontend does not expose app.loadGraphData/app.graphToPrompt");
      }
      await app.loadGraphData(graph);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const result = await app.graphToPrompt();
      if (!result || typeof result !== "object" || !result.output) {
        throw new Error("app.graphToPrompt() did not return { workflow, output }");
      }
      return result;
    }, workflow);
    await fs.writeFile(outputPath, JSON.stringify(converted, null, 2), "utf8");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
