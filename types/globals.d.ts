/*
  Ambient declarations for the globals Moodshop's plain scripts hang off
  `window`. Nothing here ships to the browser — it exists so
  `npx tsc -p jsconfig.json` can type-check the real .js files from their
  JSDoc, without turning the site into a TypeScript project that Vercel
  would have to build.
*/

interface MoodshopTheme {
  card: string;
  cardInk: string;
  accent: string;
  accent2?: string;
  colors?: string[];
  ink?: string;
  light?: boolean;
}

interface MoodshopFeeling {
  slug: string;
  name: string;
  emoji: string;
  shortDescription: string;
  whyFits: string;
  related: string[];
  product: string;
  productNote: string | null;
  theme: MoodshopTheme;
}

interface MoodshopRecommendation {
  primaryMood: MoodshopFeeling;
  secondaryMoods: MoodshopFeeling[];
  explanation: string;
  scores: Record<string, number>;
}

interface MoodshopRecommendApi {
  feelings: MoodshopFeeling[];
  quiz: any;
  feeling(slug: string): MoodshopFeeling | null;
  resolveProduct(f: string | MoodshopFeeling): { mood: string; note: string | null; href: string } | null;
  getMoodRecommendation(answers: Record<string, number>): MoodshopRecommendation | null;
  ofTheDay<T>(pool: T[], now?: Date): T | null;
  cycle<T>(list: T[], n: number): T | null;
}

interface Window {
  /** Vercel Web Analytics, injected by /_vercel/insights/script.js */
  va?: (event: string, payload?: any) => void;
  /** Datafast, injected by datafa.st */
  datafast?: (goal: string, props?: any) => void;
  /** analytics.js */
  msTrack?: (name: string, props?: any) => void;
  /** moods-data.js — the eight purchasable pieces */
  MOODSHOP?: any;
  /** feelings-data.js — the wider feeling taxonomy, quiz and wheel */
  MOODSHOP_FEELINGS?: any;
  /** tool-content.js — thoughts, message blocks, send lines, 2AM prompts */
  MOODSHOP_TOOLCONTENT?: any;
  /** recommend.js */
  MoodshopRecommend?: MoodshopRecommendApi;
}
