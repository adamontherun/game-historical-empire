import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "playwright-report", "test-results"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-syntax": [
        "error",
        {
          selector: "BinaryExpression[operator='/'][right.value=1000]",
          message: "Price maths (/1000) must go through src/lib/format.ts — see K2 / B7",
        },
        {
          selector: "BinaryExpression[operator='/'][right.value=10000]",
          message: "BPS maths (/10000) must go through src/lib/format.ts — see K2",
        },
        {
          selector: "CallExpression[callee.name='waitForTimeout']",
          message: "No waitForTimeout in critical path — wait on data-reveal-state / data-testid (B8/S2)",
        },
      ],
    },
  },
  {
    files: ["src/lib/format.ts"],
    rules: {
      "no-restricted-syntax": "off",
    },
  },
);
