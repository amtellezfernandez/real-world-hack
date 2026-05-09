import { describe, expect, test } from "bun:test";

import { resolveReplayImageUrl } from "./replay-assets";

describe("resolveReplayImageUrl", () => {
  test("maps backend replay image references to bundled demo assets", () => {
    expect(resolveReplayImageUrl("assets/demo/workcell-clear.svg")).toEndWith(
      "/assets/demo/workcell-clear.svg",
    );
    expect(resolveReplayImageUrl("assets/demo/workcell-blocked.svg")).toEndWith(
      "/assets/demo/workcell-blocked.svg",
    );
  });

  test("fails loudly for unknown replay asset references", () => {
    expect(() => resolveReplayImageUrl("camera/live")).toThrow(
      "Unknown replay image reference: camera/live",
    );
  });
});
