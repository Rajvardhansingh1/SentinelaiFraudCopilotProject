import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Skeleton } from "./skeleton";

describe("Skeleton", () => {
  it("renders a div with the pulse animation class", () => {
    const { container } = render(<Skeleton className="h-4 w-32" />);
    const el = container.firstElementChild;
    expect(el).not.toBeNull();
    expect(el?.className).toContain("animate-pulse");
    expect(el?.className).toContain("h-4");
    expect(el?.className).toContain("w-32");
  });
});
