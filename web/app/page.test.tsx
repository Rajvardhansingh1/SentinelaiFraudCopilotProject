import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/landing/network-hero-3d", () => ({
  NetworkHero3D: () => <div data-testid="hero-3d" />,
}));

import Home from "./page";

describe("Home (landing page)", () => {
  it("renders the hero headline, walkthrough section, and sign-up CTA", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(screen.getAllByText(/proxy/i).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /sign up|get started/i }).length).toBeGreaterThan(0);
  });
});
