export function prettyJson(value: unknown): string {
  try {
    const rendered = JSON.stringify(value, null, 2);
    return rendered ?? "null";
  } catch (error) {
    return "\"<unserializable>\"";
  }
}

export function truncate(text: string, max = 56): string {
  if (text.length <= max) {
    return text;
  }
  return `${text.slice(0, Math.max(0, max - 3))}...`;
}
