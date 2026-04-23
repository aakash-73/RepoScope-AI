import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Optional: Specific cleanup or mocks
afterEach(() => {
  cleanup();
});
