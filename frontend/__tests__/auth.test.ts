import { beforeEach, describe, expect, it } from "vitest";

import {
  clearToken,
  getToken,
  getUser,
  isAuthenticated,
  setToken,
  setUser,
} from "@/lib/auth";

describe("auth", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("stores and retrieves token", () => {
    setToken("abc");
    expect(getToken()).toBe("abc");
    expect(isAuthenticated()).toBe(true);
  });

  it("stores and retrieves user", () => {
    setUser({ id: 1, email: "a@b.com", name: "A" });
    expect(getUser()).toEqual({ id: 1, email: "a@b.com", name: "A" });
  });

  it("clearToken removes both token and user", () => {
    setToken("abc");
    setUser({ id: 1, email: "a@b.com", name: "A" });
    clearToken();
    expect(getToken()).toBeNull();
    expect(getUser()).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });

  it("getUser returns null when stored JSON is malformed", () => {
    window.localStorage.setItem("jobhunter_user", "not-json{");
    expect(getUser()).toBeNull();
  });
});
