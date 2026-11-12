const ALLOWED_EXTENSIONS = new Set([
  "txt",
  "md",
  "csv",
  "json",
  "html",
  "css",
  "js",
  "ts",
  "tsx",
  "jsx",
  "py",
  "pdf",
  "docx",
  "png",
  "jpg",
  "jpeg",
]);

export function validateDeliverableFiles(
  incoming: File[],
  existingCount: number,
  maxFiles = 5,
  maxBytes = 5 * 1024 * 1024,
): { accepted: File[]; errors: string[] } {
  const accepted: File[] = [];
  const errors: string[] = [];

  for (const file of incoming) {
    if (existingCount + accepted.length >= maxFiles) {
      errors.push(`Maximum ${maxFiles} files allowed per submission.`);
      break;
    }
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      errors.push(`${file.name}: unsupported file type (.${ext || "unknown"}).`);
      continue;
    }
    if (file.size > maxBytes) {
      errors.push(`${file.name}: exceeds 5 MB limit.`);
      continue;
    }
    accepted.push(file);
  }

  return { accepted, errors };
}
