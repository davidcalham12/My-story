/// <reference types="vite/client" />

// Vite's own ambient types: `import.meta.glob`, `?raw` imports, `import.meta.env`.
// The project had none, so anything reaching for the bundler's API type-checked
// as an error while running perfectly — which is the worst of both, because it
// pushes you toward a node-shaped workaround and a dependency you do not need.
