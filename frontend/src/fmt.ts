const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
export const money = (n: number) => usd.format(n);
export const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
export const moneyIn = (n: number, currency: string) => new Intl.NumberFormat("en-US", { style: "currency", currency }).format(n);

// Let a long rule name wrap at its separators, not in the middle of a word.
export const breakable = (s: string) => s.replace(/([_:])/g, "$1\u200b");
