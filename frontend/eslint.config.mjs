import { FlatCompat } from "@eslint/eslintrc";

// next lint is deprecated as of Next 15 and removed in 16 (audit M6) — this
// is the flat-config replacement create-next-app itself scaffolds for Next
// 15+. FlatCompat lets eslint-config-next's legacy "extends" style config
// work under ESLint 9's flat config system.
const compat = new FlatCompat({
  baseDirectory: import.meta.dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals"),
  {
    ignores: [".next/**", "node_modules/**"],
  },
];

export default eslintConfig;
