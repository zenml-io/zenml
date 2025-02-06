---
description: How to migrate your ZenML code to the newest version.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# ♻ Migration guide

Migrations are necessary for ZenML releases that include breaking changes, which are currently all releases that increment the minor version of the release, e.g., `0.X` -> `0.Y`. Furthermore, all releases that increment the first non-zero digit of the version contain major breaking changes or paradigm shifts that are explained in separate migration guides below.

## Release Type Examples

* `0.40.2` to `0.40.3` contains _no breaking changes_ and requires no migration whatsoever,
* `0.40.3` to `0.41.0` contains _minor breaking changes_ that need to be taken into account when upgrading ZenML,
* `0.39.1` to `0.40.0` contains _major breaking changes_ that introduce major shifts in how ZenML code is written or used.

## Major Migration Guides

The following guides contain detailed instructions on how to migrate between ZenML versions that introduced major breaking changes or paradigm shifts. The migration guides are sequential, meaning if there is more than one migration guide between your current version and the latest release, follow each guide in order.

* [Migration guide 0.13.2 → 0.20.0](migration-zero-twenty.md)
* [Migration guide 0.23.0 → 0.30.0](migration-zero-thirty.md)
* [Migration guide 0.39.1 → 0.41.0](migration-zero-forty.md)
* [Migration guide 0.58.2 → 0.60.0](migration-zero-sixty.md)

## Release Notes

For releases with minor breaking changes, e.g., `0.40.3` to `0.41.0`, check out the official [ZenML Release Notes](https://github.com/zenml-io/zenml/releases) to see which breaking changes were introduced.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
