/**
 * Authenticated file download utility.
 *
 * Fetches a presigned URL from the API, then opens it directly
 * in the browser (bypasses CORS since it's a direct navigation).
 * Falls back to blob download for local dev (non-S3 responses).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function downloadFile(
  downloadUrl: string,
  getToken: () => Promise<string | null>,
  filename?: string
): Promise<void> {
  const token = await getToken();
  if (!token) {
    throw new Error("Not authenticated");
  }

  // Ensure the URL is absolute
  const url = downloadUrl.startsWith("http")
    ? downloadUrl
    : `${API_BASE}${downloadUrl}`;

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    redirect: "manual",
  });

  if (!res.ok && res.status !== 0) {
    throw new Error(`Download failed: ${res.status}`);
  }

  const contentType = res.headers.get("Content-Type") || "";

  // If the response is JSON with a download_url, open it directly (S3/R2)
  if (contentType.includes("application/json")) {
    const data = await res.json();
    if (data.download_url) {
      // Open presigned URL directly — bypasses CORS
      window.open(data.download_url, "_blank");
      return;
    }
  }

  // Fallback: blob download (local dev when file is served directly)
  if (!filename) {
    const disposition = res.headers.get("Content-Disposition");
    if (disposition) {
      const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match) {
        filename = match[1].replace(/['"]/g, "");
      }
    }
    if (!filename) {
      filename = downloadUrl.split("/").pop() || "download";
    }
  }

  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}
