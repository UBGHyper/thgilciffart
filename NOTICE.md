# A note on licensing

`LICENSE` (MIT) covers this repository's **code**: the site (`index.html`,
`assets/`), the manifest generator (`scripts/`), and the data files that describe
where papers live.

It does not, and cannot, license the **exam papers themselves**. Trial papers are
written by individual NSW schools and remain their copyright; official HSC past
papers are published by NESA. Neither this project nor THSC holds rights to that
content — it's shared informally within the HSC community because schools have
generally tolerated it for study purposes, not because it's been released under an
open license.

In practice:

- **Subjects already hosted in this repo** (Biology, Chemistry, Physics,
  Mathematics Advanced/Ext1/Ext2/Standard, Miscellaneous) contain PDF copies.
  These predate this change and are left as-is.
- **Subjects added by this change** (see `Changelog.md`) are **link-only**:
  `data/manifest.json` points at copies already published on
  [thsc.zaxu.xyz](https://thsc.zaxu.xyz/) rather than duplicating them here. No new
  paper content was copied into this repository.

If you're a school and want a paper removed from where it's actually hosted
(THSC/zaxu), this repo can't action that directly — it only links out — but you can
open an issue here and we'll remove the link.
