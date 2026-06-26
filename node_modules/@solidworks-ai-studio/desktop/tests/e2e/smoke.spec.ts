import { expect, test } from "@playwright/test";

test("desktop renderer smoke", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "SolidWorks AI Studio" })).toBeVisible();
  await page.getByRole("button", { name: /进入工作台/i }).click();
  await expect(page.getByRole("heading", { name: /自动化工作台/i })).toBeVisible();
});
