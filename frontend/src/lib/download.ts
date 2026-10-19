import api from "@/lib/api";

/** `attachment; filename="report.pdf"` → `report.pdf` */
export function filenameFromDisposition(header: string | undefined | null): string | null {
  if (!header) return null;
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim());
    } catch {
      // Fall through to the plain form.
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1].trim() : null;
}

/**
 * Download a file from an authenticated API endpoint. A plain link cannot be
 * used because the API authenticates with a bearer token, not a cookie.
 */
export async function downloadFromApi(path: string, fallbackName: string): Promise<void> {
  const response = await api.get<Blob>(path, { responseType: "blob" });
  const name = filenameFromDisposition(response.headers["content-disposition"]) ?? fallbackName;

  const url = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Give the browser a moment to start the download before releasing it.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
