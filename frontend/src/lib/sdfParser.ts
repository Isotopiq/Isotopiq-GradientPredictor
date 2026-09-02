/** Lightweight SDF parser — splits on $$$$, extracts molfile + properties. */

export interface SdfRecord {
  molfile: string;
  properties: Record<string, string>;
}

export function parseSdf(content: string): SdfRecord[] {
  const records: SdfRecord[] = [];
  const blocks = content.split(/\$\$\$\$/);

  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;

    // Split molfile from properties
    const lines = trimmed.split(/\r?\n/);
    // Molfile: lines until we hit ">  <PROPERTY>" or "M  END"
    let molEnd = 0;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('M  END')) {
        molEnd = i + 1;
        break;
      }
      if (lines[i].match(/^>\s*</)) {
        molEnd = i;
        break;
      }
    }

    if (molEnd === 0) {
      // No M  END and no properties — treat entire block as molfile
      molEnd = lines.length;
    }

    const molfile = lines.slice(0, molEnd).join('\n');
    const properties: Record<string, string> = {};

    // Parse properties after molfile
    let i = molEnd;
    while (i < lines.length) {
      const line = lines[i];
      const match = line.match(/^>\s*<([^>]+)>/);
      if (match) {
        const key = match[1];
        const value = lines[i + 1]?.trim() || '';
        properties[key] = value;
        i += 2;
      } else {
        i++;
      }
    }

    records.push({ molfile, properties });
  }

  return records;
}

/** Parse CSV with name,smiles columns */
export function parseCompoundCsv(content: string): Array<{ name?: string; smiles: string }> {
  const lines = content.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return [];

  const header = lines[0].toLowerCase();
  const hasHeader = header.includes('smiles') || header.includes('name');
  const startIdx = hasHeader ? 1 : 0;

  const results: Array<{ name?: string; smiles: string }> = [];
  for (let i = startIdx; i < lines.length; i++) {
    const parts = lines[i].split(',').map((s) => s.trim());
    if (parts.length < 1) continue;

    if (hasHeader) {
      const cols = header.split(',').map((s) => s.trim());
      const smilesIdx = cols.findIndex((c) => c.includes('smiles'));
      const nameIdx = cols.findIndex((c) => c.includes('name'));
      if (smilesIdx >= 0 && parts[smilesIdx]) {
        results.push({
          smiles: parts[smilesIdx],
          name: nameIdx >= 0 ? parts[nameIdx] : undefined,
        });
      }
    } else {
      // Assume first column is smiles
      if (parts[0]) results.push({ smiles: parts[0], name: parts[1] });
    }
  }
  return results;
}
