const DEMO_ASSET_REF_PREFIX = "assets/demo/";

const replayImageAssets = [
  {
    fileName: "workcell-clear.svg",
    url: "/assets/demo/workcell-clear.svg",
  },
  {
    fileName: "workcell-blocked.svg",
    url: "/assets/demo/workcell-blocked.svg",
  },
] as const;

const replayImageUrls = new Map(
  replayImageAssets.map(({ fileName, url }) => [
    `${DEMO_ASSET_REF_PREFIX}${fileName}`,
    url,
  ]),
);

/** Resolve backend replay image references to bundled frontend asset URLs. */
export function resolveReplayImageUrl(imageRef: string): string {
  const imageUrl = replayImageUrls.get(imageRef);

  if (imageUrl === undefined) {
    throw new Error(`Unknown replay image reference: ${imageRef}`);
  }

  return imageUrl;
}
