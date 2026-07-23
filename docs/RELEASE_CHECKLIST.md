# Release Checklist

## Quality

- [ ] Ruff lint and format checks pass.
- [ ] Mypy strict type checking passes.
- [ ] Unit, integration, privacy, regression, and E2E tests pass.
- [ ] Source coverage is at least 80%.
- [ ] Wheel and sdist build successfully.
- [ ] Release artifacts install and run in a clean temporary environment.

## Product

- [ ] All 15 seeded sample findings are detected within the false-positive cap.
- [ ] Source workbook hashes remain unchanged.
- [ ] Formula-to-constant replacement is present in version diff output.
- [ ] HTML, JSON, and annotated workbook exports are manually reviewed.
- [ ] Streamlit keyboard labels, contrast, and responsive layout are checked.

## Supply chain and privacy

- [ ] Dependency audit and secret scan pass.
- [ ] Package and release archive contain no environment files, caches, tokens,
      private data, or build scratch files.
- [ ] `SHA256SUMS.txt` matches every release asset.

## Git and GitHub

- [ ] Worktree is clean.
- [ ] Package, changelog, tag, and release versions all equal `0.1.0`.
- [ ] Author and committer match the authenticated GitHub account.
- [ ] No `Co-authored-by` trailers or unknown contributors exist.
- [ ] Main CI and security workflows are green.
- [ ] `v0.1.0` is annotated and points to the intended main commit.
- [ ] GitHub Release is public, not a draft, and assets are downloadable.
