# Swansea ISOC Committee Hub

A separate committee workspace prototype. Neither discount-directory repository is modified by this project.

## Preview and private entry

- `demo.html` is an interactive **sample-data preview**. Role switching is a design-review tool, not authentication. No real finance records, private sheet links, receipts or live committee tasks are included.
- `index.html` is the private hub's sign-in shell. It stays locked until the authenticated backend is configured. Publishing these files does not enable Google login or authorise committee access.

Sample action edits stay in this browser. Sample well-being messages are temporary and are not sent to anyone. Do not enter personal concerns, bank details or private committee information in the public demo.

## Features

My Space, action points, media requests, reimbursements, shared files, who's who, well-being and proposed values. The finance desk is a separate permission intended for the General Secretaries, not all executives. Live permissions must be enforced by the server.

## Deployment

GitHub Pages serves the static interface only. The deployment workflow publishes the `site/` folder after browser checks. Google authentication, email notifications, ClickUp and OneDrive are not connected yet.

## Source files

`site/index.html`, `site/demo.html`, `site/hub.js`, `site/hub.css`, `site/config.js` and `site/assets/`. Only public configuration belongs in the repository. Keep the finance workbook, private setup bundle, email allowlist and credentials out of GitHub.

The ISOC logo artwork was supplied by the user. Fonts use system font stacks; no font files are included.
