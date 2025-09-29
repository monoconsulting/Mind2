# System Documentation Instructions  

AI INSTRUCTIONS (DO NOT REMOVE)

**Template Notice:**  
This document is a template. You **must** replace all occurrences of `XXXX` with your project name and fill in the placeholders with actual values.  
Validate ports with Atlas first — see **@CHECK_PORTS_API.md**.  

---

## Purpose  

This document describes **how to fill out system documentation** for every project.  
The goal is to ensure a **complete, standardized, and high-quality description** of each system's configuration, dependencies, and functionality.  

This document is editable by both AI and humans. **Follow these rules carefully:**  

1. **This is a TEMPLATE.** Replace placeholders with project-specific values.  
2. The `"XXXX"` prefix MUST be replaced with the actual PROJECT NAME (`kebab_case` or `snake_case`) in the filname and in the information below.  
3. **Ports must NOT be assigned until verified** against the authoritative Atlas port list.  
   
   - See `@CHECK_PORTS_API.md` for the verification workflow.  
4. **Do NOT hardcode host ports or secrets** in code or documentation.  
   
   - Use environment variables and `.env` / `.env.example` files.  
5. **Never delete sections.**  
   
   - If a section is deprecated or not relevant, strike it through and explain why.  
   - Example:  
     ```markdown
     ~~This section is not needed for this system.~~
     ```
6. Update the **CHANGELOG** table (increment version in `0.1` steps) whenever content changes.  
7. Keep consistency across all documentation:  
   - PORTS  
   - API bases  
   - Endpoints  
   - OpenAPI definitions  
   - Environment variables  
   - Security requirements  
8. Save the file in the following folder with the correct name:  
   `@docs/systemdocs/PROJECT_NAME_DOCUMENTATION_NAME.md`  
   
   - Example: `mind_endpoints_v1.4.md`  
9. Always validate ports, endpoints, and environment variables before committing.  

---

## Location of Documentation  

- All system documentation is located under the directory:  
  `docs/SYSTEMDOCS/`  

- Each file in this directory represents a **specific part of the system** (architecture, endpoints, dependencies, environment variables, etc.) that must be documented.  

---

## Templates  

- In the `templates` directory, you will find **template files** for each documentation type.  
- Naming convention:  
xxxx_<FUNCTION_NAME>_<version>.md

makefile
Kopiera kod
Example:  
xxxx_architecture_v1.md
xxxx_dependencies_v2.md

pgsql
Kopiera kod

- Each template contains **predefined sections** with placeholder text and instructions.  

---

## How to Fill Out the Templates  

1. **Open each template file** and fill in all placeholders with real, project-specific information.  
2. **Do not remove any section.**  
 - If a section is irrelevant, strike it through and explain why.  
3. **Be detailed and precise.**  And keep yourself short.
 - The goal is to provide a **complete overview** of the system that allows another person to fully understand its configuration and functionality without additional clarification.  
4. **Follow the given structure** in headings, tables, and formatting.  
5. **Use consistent terminology** across all documentation files in the project.  
6. If you create a new version, **increment the version number**, copy the file, and document the change in the CHANGELOG table.  

---

## Example File Header  

```markdown
# XXXX — API Bases & Service URLs (Template)

File: XXXX_API_BASES.md  
Version: 0.0
Changelog Table
Every documentation file must include a CHANGELOG table at the bottom:

Date	Filename	Version	Changes	Author
YYYY-MM-DD	PROJECT_NAME_DOCUMENTATION_NAME_v.1.1.md	1.1	Write the changes that are made in the file here	If you are an agent, write what agent you are (example - Gemini, ChatGPT-5)

Objective
Following these instructions will ensure that all projects are consistently documented, version-controlled, and fully traceable — making it easy for developers, project managers, and stakeholders to understand:

System architecture

APIs and endpoints

Ports and network configurations

Dependencies and integrations

Security considerations

Operational requirements
