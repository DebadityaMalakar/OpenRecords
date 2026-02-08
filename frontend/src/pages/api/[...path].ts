import type { NextApiRequest, NextApiResponse } from "next";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export const config = {
  api: {
    bodyParser: false, // Forward raw body for file uploads etc.
    responseLimit: false,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { path } = req.query;
  const target = Array.isArray(path) ? path.join("/") : path || "";
  const url = `${BACKEND}/api/${target}${
    req.url?.includes("?")
      ? "?" + req.url.split("?").slice(1).join("?")
      : ""
  }`;

  // Forward headers, including cookies
  const headers: Record<string, string> = {};
  for (const [key, value] of Object.entries(req.headers)) {
    if (typeof value === "string") {
      headers[key] = value;
    } else if (Array.isArray(value)) {
      headers[key] = value.join(", ");
    }
  }
  // Remove host header so the backend gets the right one
  delete headers["host"];

  try {
    // Read request body as buffer
    const chunks: Buffer[] = [];
    for await (const chunk of req) {
      chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
    }
    const body = chunks.length > 0 ? Buffer.concat(chunks) : undefined;

    const response = await fetch(url, {
      method: req.method || "GET",
      headers,
      body: req.method !== "GET" && req.method !== "HEAD" ? body : undefined,
      // @ts-ignore -- duplex needed for streaming body
      duplex: "half",
    });

    // Forward response status
    res.status(response.status);

    // Forward response headers (especially Set-Cookie!)
    response.headers.forEach((value, key) => {
      // Don't forward transfer-encoding since Next.js handles that
      if (key.toLowerCase() === "transfer-encoding") return;
      res.setHeader(key, value);
    });

    // Forward response body
    const responseBody = await response.arrayBuffer();
    res.send(Buffer.from(responseBody));
  } catch (error) {
    console.error("Proxy error:", error);
    res.status(502).json({ detail: "Backend unavailable" });
  }
}
