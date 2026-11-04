import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// A small, unique, valid PDF generated on the fly.
function makePdf(text: string): Buffer {
  const content = `BT /F1 12 Tf 72 720 Td (${text}) Tj ET`;
  const objs = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((o, i) => {
    offsets.push(pdf.length);
    pdf += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = pdf.length;
  pdf += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  offsets.forEach((o) => (pdf += `${String(o).padStart(10, "0")} 00000 n \n`));
  pdf += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(pdf, "latin1");
}

test("upload a PDF, it gets indexed, then delete it", async ({ page }) => {
  const stamp = Date.now();
  await login(page, "bob@dupont.test");
  await page.goto("/documents");
  await page.getByRole("button", { name: "Upload PDF" }).click();
  await page.getByLabel(/PDF file/).setInputFiles({
    name: `e2e-${stamp}.pdf`,
    mimeType: "application/pdf",
    buffer: makePdf(`E2E test document ${stamp}: the parking fee is 120 EUR per month.`),
  });
  await page.getByLabel("Title (optional)").fill(`E2E upload ${stamp}`);
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  const row = page.getByRole("row", { name: new RegExp(`E2E upload ${stamp}`) });
  await expect(row).toBeVisible();
  await expect(row.getByTestId("doc-status")).toHaveText("Ready", { timeout: 90_000 });

  await row.getByRole("link").click();
  await expect(page.getByRole("heading", { name: `E2E upload ${stamp}` })).toBeVisible();
  await page.getByRole("button", { name: "Delete" }).click();
  await page.getByRole("button", { name: "Delete permanently" }).click();
  await expect(page).toHaveURL(/\/documents$/);
  await expect(page.getByText(`E2E upload ${stamp}`)).toHaveCount(0);
});

test("non-PDF upload is rejected with a clear message", async ({ page }) => {
  await login(page, "bob@dupont.test");
  await page.goto("/documents");
  await page.getByRole("button", { name: "Upload PDF" }).click();
  await page.getByLabel(/PDF file/).setInputFiles({
    name: "fake.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("MZ this is not a pdf"),
  });
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "not a valid PDF" })).toBeVisible();
});

test("ask the assistant and get a cited answer", async ({ page }) => {
  test.setTimeout(300_000);
  await login(page, "alice@dupont.test");
  await page.goto("/assistant");
  await page.getByRole("button", { name: "New conversation" }).first().click();
  await expect(page).toHaveURL(/\/assistant\/[0-9a-f-]{36}/);
  await page.getByLabel("Your question").fill(
    "What notice period is required to terminate the Globex agreement for convenience?",
  );
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("thinking")).toBeVisible();
  const answer = page.getByTestId("message-assistant").last();
  await expect(answer).toBeVisible({ timeout: 240_000 });
  await expect(answer.getByTestId("sources")).toContainText("Master Services Agreement");
  await expect(answer.getByTestId("sources")).toContainText(/page \d/);
  // With the real local LLM, also check the content (CI uses a fake model).
  const expected = process.env.E2E_FAKE_LLM ? /From the documents/ : /90|ninety/i;
  await expect(answer).toContainText(expected);

  // Persisted: reload and the conversation is still there.
  await page.reload();
  await expect(page.getByTestId("message-assistant").last()).toContainText(expected);
});
