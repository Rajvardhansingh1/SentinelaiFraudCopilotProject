import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PublicHeader } from "./public-header";

describe("PublicHeader", () => {
  it("renders nav links and auth buttons", () => {
    render(<PublicHeader />);
    expect(screen.getByRole("link", { name: /about/i })).toHaveAttribute("href", "/about");
    expect(screen.getByRole("link", { name: /install/i })).toHaveAttribute("href", "/install");
    expect(screen.getByRole("link", { name: /log in/i })).toHaveAttribute("href", "/login");
    expect(screen.getByRole("link", { name: /sign up/i })).toHaveAttribute("href", "/signup");
  });
});
