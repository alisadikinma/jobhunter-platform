import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { Sidebar } from "@/components/shared/Sidebar";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ me: { email: "x@y.z" }, logout: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => "/jobs" }));

describe("Sidebar", () => {
  test("renders exactly 3 nav links (Jobs, Applications, Settings)", () => {
    render(<Sidebar />);
    const allLinks = screen.getAllByRole("link");
    const internalLinks = allLinks.filter((a) =>
      a.getAttribute("href")?.startsWith("/"),
    );
    // Logo (1) + 3 nav items = 4 anchor tags total. Filter logo by text.
    const navLinks = internalLinks.filter((a) => a.textContent !== "JobHunter");
    expect(navLinks).toHaveLength(3);

    const hrefs = navLinks.map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["/jobs", "/applications", "/settings"]);
  });

  test("logo links to /jobs", () => {
    render(<Sidebar />);
    const logo = screen.getByRole("link", { name: "JobHunter" });
    expect(logo.getAttribute("href")).toBe("/jobs");
  });

  test("sign-out button exists", () => {
    render(<Sidebar />);
    expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
  });
});
