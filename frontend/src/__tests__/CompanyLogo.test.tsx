import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { CompanyLogo } from "@/components/shared/CompanyLogo";

describe("CompanyLogo", () => {
  test("uses logoUrl when provided", () => {
    render(
      <CompanyLogo
        logoUrl="https://example.com/logo.png"
        domain="example.com"
        name="Acme"
      />,
    );
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://example.com/logo.png");
  });

  test("falls back to favicon API when only domain provided", () => {
    render(<CompanyLogo logoUrl={null} domain="example.com" name="Acme" />);
    const img = screen.getByRole("img");
    expect(img.getAttribute("src")).toContain("google.com/s2/favicons");
    expect(img.getAttribute("src")).toContain("domain=example.com");
  });

  test("renders building icon placeholder when both null", () => {
    const { container } = render(
      <CompanyLogo logoUrl={null} domain={null} name="Acme" />,
    );
    expect(container.querySelector("svg")).toBeTruthy();
    expect(screen.queryByRole("img")).toBeNull();
  });
});
