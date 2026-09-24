import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import InstallPage from "./page";

describe("InstallPage", () => {
  it("shows the real setup commands from README.md", () => {
    render(<InstallPage />);
    expect(screen.getByText(/pip install -r requirements.txt/)).toBeInTheDocument();
    expect(screen.getByText(/uvicorn proxy\.main:app --port 8000/)).toBeInTheDocument();
    expect(screen.getByText(/npm run dev/)).toBeInTheDocument();
  });
});
