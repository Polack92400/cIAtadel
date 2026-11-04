import { expect, test } from "@playwright/test";
import { login, PASSWORD } from "./helpers";

test("unauthenticated users are redirected to login", async ({ page }) => {
  await page.goto("/documents");
  await expect(page).toHaveURL(/\/login\?next=%2Fdocuments/);
});

test("wrong password shows a generic error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Work email").fill("alice@dupont.test");
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Invalid email or password" })).toBeVisible();
});

test("login, see the firm dashboard, logout", async ({ page, context }) => {
  await login(page, "alice@dupont.test");
  await expect(page.getByRole("heading", { name: /Dupont/ })).toBeVisible();
  await expect(page.getByText("Recent documents")).toBeVisible();
  // Tokens are HttpOnly: invisible to page scripts.
  const visible = await page.evaluate(() => document.cookie);
  expect(visible).not.toContain("ciatadel_access");
  const cookies = await context.cookies();
  expect(cookies.find((c) => c.name === "ciatadel_access")?.httpOnly).toBe(true);

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
  void PASSWORD;
});
