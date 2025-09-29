# System Docs - Instructions

## **Changelog**

| Date       | Filename                          | Version | Changes       | Author            |
| ---------- | --------------------------------- | ------- | ------------- | ----------------- |
| 2025-09-21 | SYSTEM_DOCS_INSTRUCTIONS.v.1.0.md | 1.0     | First version | Mattias Cederlund |

This document describes **how to fill out system documentation** for every project.
 The goal is to ensure a **complete, consistent, and high-quality description** of each system's configuration, dependencies, and functionality.

## Location of Documentation

- All system documentation is located under the directory:
   `docs/SYSTEMDOCS/`
- In this directory, you will find multiple files — each one represents a key aspect of the system that must be documented.

## Templates

- In the `templates` directory, `docs/SYSTEMDOCS/templates`you will find template files used to create the documentation.

- Each template follows the naming convention:

  ```
  xxxx_<FUNCTION_NAME>_<version>.md
  ```

  Example:

  ```
  xxxx_architecture_v1.md
  xxxx_dependencies_v2.md
  ```

- Each file contains pre-written **template text** with guidance and placeholder sections.

## How to Fill Out the Templates

1. **Do not delete any information** from the file.

   - If a section is not applicable to your project, cross it out and clearly state that it is not required.

   - Example:

     ```
     ~~This section is not needed for this system.~~
     ```

2. **Be as detailed and precise as possible.**

   - Your goal is to give a reader a **complete overview** of the system setup and its functionality without requiring additional explanations.

3. **Use clear, structured language.**

   - Follow the format already defined in the template (headings, bullet points, code blocks, etc.).

4. **Keep consistency across projects.**

   - Always use the same terminology and structure as provided in the template files.
   - This ensures that all project documentation remains comparable and easy to navigate.

5. **Version control.**

   - Do not change the filename structure or version number.
   - If you need to create a new version, copy the file, increment the version number, and fill in the updated information.

## Objective

By following these steps, you will produce a **comprehensive and standardized system documentation package** that can be used by project managers, developers, and stakeholders to quickly understand the system's architecture, integrations, dependencies, and operational requirements.