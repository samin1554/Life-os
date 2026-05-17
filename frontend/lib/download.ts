/**
 * Authenticated file download utility.
 *
 * Uses fetch with Authorization header to download files from the API,
 * then triggers a browser download via a temporary blob URL.
 * This is needed because <a href> tags can't send auth headers.
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
  });

  if (!res.ok) {
    throw new Error(`Download failed: ${res.status}`);
  }

  // Extract filename from Content-Disposition header if not provided
  if (!filename) {
    const disposition = res.headers.get("Content-Disposition");
    if (disposition) {
      const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (match) {
        filename = match[1].replace(/['"]/g, "");
      }
    }
    if (!filename) {
      // Fallback: extract from URL
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

  // Clean up blob URL after short delay
  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
}
