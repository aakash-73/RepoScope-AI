import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";
import { describe, it, expect, vi } from "vitest";

// Mock the GraphPage since it might have complex dependencies (like xyflow)
vi.mock("../pages/GraphPage", () => ({
  default: () => <div data-testid="graph-page">Mock Graph Page</div>,
}));

describe("App Component", () => {
  it("renders the main layout and the default route", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByTestId("graph-page")).toBeInTheDocument();
  });

  it("redirects unknown routes to home", () => {
    render(
      <MemoryRouter initialEntries={["/unknown"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByTestId("graph-page")).toBeInTheDocument();
  });
});
