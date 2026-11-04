import { expect, test } from "@playwright/test";
import { login } from "./helpers";

test("viewer cannot reach administration or upload", async ({ page }) => {
  await login(page, "carol@dupont.test");
  await expect(page.getByRole("link", { name: "Firm administration" })).toHaveCount(0);
  await page.goto("/admin");
  await expect(page.getByText(/restricted to administrators/)).toBeVisible();
  await page.goto("/documents");
  await expect(page.getByRole("button", { name: "Upload PDF" })).toHaveCount(0);
});

test("another firm's document is not accessible by URL", async ({ page, request }) => {
  // Find a Northwind document id as Dave...
  await login(page, "dave@northwind.test");
  await page.goto("/documents");
  await page.getByRole("link", { name: /Audit engagement letter/ }).click();
  await expect(page).toHaveURL(/\/documents\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: /Audit engagement letter/ })).toBeVisible();
  const northwindUrl = page.url();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  // ...then try it as Alice (Dupont).
  await login(page, "alice@dupont.test");
  await page.goto(northwindUrl.replace(/^https?:\/\/[^/]+/, ""));
  await expect(page.getByText(/does not exist or you do not have access/)).toBeVisible();
  void request;
});

test("ethical wall: member without access does not see the restricted matter", async ({ page }) => {
  await login(page, "bob@dupont.test");
  await page.goto("/documents");
  await expect(page.getByRole("link", { name: /Master Services Agreement/ })).toBeVisible();
  await expect(page.getByText(/Commercial lease/)).toHaveCount(0);
});
