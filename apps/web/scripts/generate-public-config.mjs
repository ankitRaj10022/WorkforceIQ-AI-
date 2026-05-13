import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const requiredKeys = [
  "NEXT_PUBLIC_WORKFORCEIQ_API_BASE_URL",
  "NEXT_PUBLIC_WORKFORCEIQ_ORGANIZATION_ID",
  "NEXT_PUBLIC_COGNITO_REGION",
  "NEXT_PUBLIC_COGNITO_USER_POOL_ID",
  "NEXT_PUBLIC_COGNITO_APP_CLIENT_ID",
  "NEXT_PUBLIC_COGNITO_DOMAIN",
  "NEXT_PUBLIC_COGNITO_CALLBACK_URL",
  "NEXT_PUBLIC_COGNITO_LOGOUT_URL",
];

function escapeValue(value) {
  return JSON.stringify(value);
}

const values = {};

for (const key of requiredKeys) {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required frontend environment variable: ${key}`);
  }
  values[key] = value;
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const outputPath = path.resolve(scriptDir, "../lib/generated-public-config.ts");

mkdirSync(path.dirname(outputPath), { recursive: true });
writeFileSync(
  outputPath,
  `export const generatedPublicConfig = {\n${requiredKeys
    .map((key) => `  ${key}: ${escapeValue(values[key])},`)
    .join("\n")}\n} as const;\n`,
  "utf8",
);
