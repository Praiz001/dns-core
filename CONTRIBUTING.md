# Contributing to dns-core

Thank you for your interest in contributing to dns-core! This document provides guidelines and best practices to help you contribute effectively.

## Development Workflow

### 1. Create a new branch for your work:
```sh
git checkout -b feat/proofread-2145-your-feature-name
```

#### Branch Naming Rules
- Use prefixes like `feat/`, `refactor/`, `fix/`, `chore/`, or `docs/` for the type of update.
- Include the ticket or issue number, e.g., ProofRead-2145.
- Add a short description, usually from the ticket title.
- All except the ticket number acronym should be in lowercase.
> Example: `feat/proofread-1234-create-login-page` or `chore/remove-unused-variables` if no ticket/issue.

### 2. Make your changes, and commit them with descriptive messages:
```sh
git commit -m "feat: your commit message"
```

#### Commit Message Rules
- Use a colon after the type of change, then your message.
- Optionally, add the ticket number in parentheses after the type.
- Example: `refactor: use a single state for formData` or `refactor(proofread-1234): use a single state for formData`
- Use imperative tense: "fix login issue", NOT "I fixed login issue" or "fixed login issue".

#### Conventional Commit Style
We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages. This ensures consistent and meaningful commit history.

- **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, etc.
- **Scope** (optional): A noun describing the section of the codebase (e.g., `api`, `ui`).
- **Description**: A short summary of the change.
- **Body** (optional): More detailed explanation.
- **Footer** (optional): For breaking changes or issue references.

Example:
```
feat(api): add user authentication endpoint

- Implement JWT token validation
- Add middleware for protected routes

Closes #123
```

## Creating a Pull Request

1. **Push your branch**: After committing your changes, push the branch to the repository.
   ```sh
   git push origin feat/proofread-2145-your-feature-name
   ```

2. **Create the PR**: Go to the repository on GitHub and create a new pull request from your branch to the `main` branch.

3. **PR Title**: Use a clear, descriptive title following the conventional commit format, e.g., `feat: add user authentication`.

4. **PR Description**:
   - Describe what changes were made and why.
   - Reference any related issues or tickets.
   - Include screenshots or examples if applicable.
   - List any breaking changes or migration steps.

5. **Code Review**: Request reviews from maintainers. Address any feedback by making additional commits to your branch.

6. **Merge**: Once approved, the PR will be merged. Delete your branch after merging.

### PR Guidelines
- Ensure all tests pass and code is properly formatted.
- Keep PRs focused on a single feature or fix.
- Update documentation if necessary.
- Follow the branch naming and commit message conventions.

For more details, refer to the [GitHub Pull Request documentation](https://docs.github.com/en/pull-requests).