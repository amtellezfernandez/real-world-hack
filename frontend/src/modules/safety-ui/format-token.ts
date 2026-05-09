/** Format backend snake-case contract tokens as concise UI labels. */
export function formatToken(value: string): string {
  const phrase = value
    .split("_")
    .map((word) => `${word.slice(0, 1).toUpperCase()}${word.slice(1)}`)
    .join(" ");

  return `${phrase.slice(0, 1)}${phrase.slice(1).toLowerCase()}`;
}
