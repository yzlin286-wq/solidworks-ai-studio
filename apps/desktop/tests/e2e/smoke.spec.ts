import { expect, test } from "@playwright/test";

test("desktop renderer smoke", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("AI Capability Workbench")).toBeVisible();
});

