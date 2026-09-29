# Permate Attribution SDK public documentation

Public integration and Maven distribution documentation for the Permate Attribution SDK for Android.

- Documentation: https://permate-global-jsc.github.io/permate-attribution-sdk-docs/
- Maven ID: `com.permate:permate-attribution`
- Maven repository: https://sdk.pmcdn1.com/maven/releases/

The page is intentionally standalone and contains no credentials or private SDK source.

## Release updates

The terminal Android stable-release workflow updates `index.html` and `release-state.json` only after the signed public audit passes and the immutable release-record head advances. A repository-scoped deploy key grants that workflow write access to this documentation repository only.

Every documentation update is checked against the public `release.json` marker and its exact six-object Maven inventory before GitHub Pages deploys it.
