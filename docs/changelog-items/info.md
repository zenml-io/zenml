# Adding a New Changelog Item

---

This guide explains how to add a new announcement/changelog item to the ZenML Changelog Widget.

## Schema Overview

Each changelog item is a JSON object with the following fields. The announcements are stored as an array of these objects.

## Required Fields

### `id` (number)

- **Type:** Number
- **Required:** Yes
- **Description:** Unique identifier for the announcement
- **Example:** `1`, `2`, `3`

### `slug` (string)

- **Type:** String
- **Required:** Yes
- **Description:** URL-friendly identifier for the announcement
- **Example:** `"new-pipeline-feature"`, `"bugfix-artifact-loading"`

### `title` (string)

- **Type:** String
- **Required:** Yes
- **Description:** The headline/title of the announcement
- **Example:** `"New Pipeline Visualization Feature"`

### `description` (string)

- **Type:** String
- **Required:** Yes
- **Description:** Detailed description of the change or feature, can use markdown
- **Example:** `"We've added a new interactive pipeline visualization that helps you understand your ML workflows better."`

### `published_at` (string)

- **Type:** ISO 8601 datetime string
- **Required:** Yes
- **Description:** The date and time when the announcement should be published
- **Format:** `YYYY-MM-DDTHH:mm:ss.sssZ` or `YYYY-MM-DDTHH:mm:ssZ`
- **Example:** `"2025-11-10T14:30:00Z"`, `"2025-11-10T14:30:00.000Z"`

## Optional Fields

### `feature_image_url` (string)

- **Type:** String
- **Required:** No
- **Description:** URL to a feature image/screenshot for the announcement
- **Example:** `"<https://zenml.io/assets/feature-image.png>"`

### `learn_more_url` (string)

- **Type:** Valid URL string
- **Required:** No
- **Validation:** Must be a valid URL format
- **Description:** Link to a blog post, article, or additional information
- **Example:** `"<https://blog.zenml.io/new-feature>"`

### `docs_url` (string)

- **Type:** Valid URL string
- **Required:** No
- **Validation:** Must be a valid URL format
- **Description:** Link to documentation for the feature
- **Example:** `"<https://docs.zenml.io/user-guide/pipelines>"`

### `published` (boolean)

- **Type:** Boolean
- **Required:** No
- **Default:** `true`
- **Description:** Whether the announcement should be visible to users
- **Example:** `true`, `false`

### `highlight_until` (string)

- **Type:** ISO 8601 datetime string
- **Required:** No
- **Description:** Date until which the announcement should be highlighted
- **Format:** `YYYY-MM-DDTHH:mm:ss.sssZ` or `YYYY-MM-DDTHH:mm:ssZ`
- **Example:** `"2025-11-20T00:00:00Z"`

### `should_highlight` (boolean)

- **Type:** Boolean
- **Required:** No
- **Default:** `false`
- **Description:** Whether to prominently highlight this announcement
- **Example:** `true`, `false`

### `video_url` (string)

- **Type:** String
- **Required:** No
- **Description:** URL to a video demonstration or explanation
- **Example:** `"<https://www.youtube.com/watch?v=example>"`

### `audience` (enum)

- **Type:** Enum (one of the specified values)
- **Required:** No
- **Default:** `"all"`
- **Allowed Values:**
  - `"pro"` - Show only to ZenML Pro users
  - `"oss"` - Show only to open-source users
  - `"all"` - Show to all users
- **Example:** `"all"`

### `labels` (array of strings)

- **Type:** Array of strings
- **Required:** No
- **Default:** `[]` (empty array)
- **Allowed Values:** Only the following labels are recognized:
  - `"feature"` - For new features
  - `"improvement"` - For enhancements to existing functionality
  - `"bugfix"` - For bug fixes
  - `"deprecation"` - For deprecated features or warnings
- **Note:** Any labels not in the allowed list will be filtered out automatically
- **Example:** `["feature"]`, `["bugfix", "improvement"]`

## Complete Example

```json
{
	"id": 42,
	"slug": "new-artifact-visualization",
	"title": "Enhanced Artifact Visualization",
	"description": "We've completely redesigned how artifacts are displayed in the dashboard, making it easier to explore your ML artifacts and their metadata.",
	"feature_image_url": "<https://zenml.io/assets/artifact-viz.png>",
	"learn_more_url": "<https://blog.zenml.io/artifact-visualization>",
	"docs_url": "<https://docs.zenml.io/user-guide/artifacts>",
	"published": true,
	"published_at": "2025-11-10T10:00:00Z",
	"highlight_until": "2025-11-17T23:59:59Z",
	"should_highlight": true,
	"video_url": "<https://www.youtube.com/watch?v=example>",
	"audience": "all",
	"labels": ["feature", "improvement"]
}
```

## Minimal Example

```json
{
	"id": 43,
	"slug": "minor-ui-fix",
	"title": "Fixed Button Alignment Issue",
	"description": "Resolved a visual bug where buttons were misaligned in the settings page.",
	"published_at": "2025-11-10T15:30:00Z"
}
```

## Tips

1. **ID Management:** Ensure each announcement has a unique ID. Use the next available number in sequence.
2. **Datetime Format:** Always use ISO 8601 format for dates. It should be in UTC, including the `Z` suffix
3. **URLs:** All URL fields (`learn_more_url`, `docs_url`) must be valid URLs or the schema validation will fail.
4. **Labels:** Use appropriate labels to help users filter and understand the type of change. Multiple labels are allowed.
5. **Highlighting:** Use `should_highlight: true` and `highlight_until` for important announcements that need extra visibility.
