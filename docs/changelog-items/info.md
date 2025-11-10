# Changelog Items

This directory contains the changelog items that are displayed in the ZenML dashboard's "What's New" section. All changelog items must follow a specific structure that is validated against the JSON schema defined in `announcement-schema.json`.

## Structure and Validation

All changelog items in `changelog.json` (located in the repository root) are automatically validated against `announcement-schema.json` when you create a pull request. The validation runs as part of our CI/CD pipeline to ensure data consistency and prevent errors in the dashboard.

## Additional Resources

For more detailed guidance on adding new changelog items, including best practices and examples, refer to the documentation in [Notion](https://www.notion.so/zenml/Adding-a-New-Changelog-Item-2a7f8dff25388085bfa8fc9fb7f601df?source=copy_link).
