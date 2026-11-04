import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/outfit/400.css";
import "@fontsource/outfit/500.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
