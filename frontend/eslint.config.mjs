import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

// next lint is deprecated as of Next 15 and removed in 16 (audit M6) — this
// is the flat-config replacement create-next-app itself scaffolds for Next
// 15+. As of eslint-config-next 16, the package exports a native flat-config
// array directly, so the old FlatCompat("next/core-web-vitals") legacy-config
// shim is no longer needed (and its circular internal plugin-config object
// broke config-schema validation under newer ESLint releases).
//
// eslint itself is pinned to the latest 9.x line, not 10.x: eslint-plugin-react
// 7.37.5 (pulled in transitively by eslint-config-next@16.3.0) still calls the
// ESLint-10-removed `context.getFilename()` API and throws on every file.
// eslint-config-next's peer range (">=9.0.0") allows this; revisit once
// eslint-plugin-react ships an ESLint 10-compatible release.
const eslintConfig = [
  ...nextCoreWebVitals,
  {
    ignores: [".next/**", "node_modules/**"],
  },
];

export default eslintConfig;
