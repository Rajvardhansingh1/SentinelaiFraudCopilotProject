import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import AboutPage from "./page";

describe("AboutPage", () => {
  it("renders the product explanation", () => {
    render(<AboutPage />);
    expect(screen.getByRole("heading", { level: 1, name: /about/i })).toBeInTheDocument();
    expect(screen.getAllByText(/sentinelai/i).length).toBeGreaterThan(0);
  });
});
