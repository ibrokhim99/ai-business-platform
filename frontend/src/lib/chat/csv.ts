export interface CsvSummary {
  name: string;
  rows: number;
  cols: number;
  headers: string[];
  preview: Array<Record<string, string>>;
}

export async function readCsvFile(file: File): Promise<CsvSummary> {
  const text = await file.text();
  const lines = text.split(/\r?\n/).filter((l) => l.length);
  if (lines.length === 0) {
    return { name: file.name, rows: 0, cols: 0, headers: [], preview: [] };
  }
  const headers = lines[0].split(',').map((h) => h.trim());
  const preview = lines.slice(1, Math.min(6, lines.length)).map((line) => {
    const values = line.split(',');
    return Object.fromEntries(headers.map((h, i) => [h, (values[i] ?? '').trim()]));
  });
  return { name: file.name, rows: lines.length - 1, cols: headers.length, headers, preview };
}
