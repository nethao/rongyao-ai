# Product Overview

Glory AI Audit System (荣耀AI审核发布系统) is an automated content processing and publishing platform designed to streamline WordPress multi-site content submission workflows.

## Core Purpose

The system automates the entire content lifecycle from email submission to WordPress publication across multiple sites (A/B/C/D stations), eliminating manual processing bottlenecks.

## Key Capabilities

- Automated email monitoring and content extraction from IMAP mailboxes
- AI-powered semantic transformation (first-person to third-person narrative conversion)
- Dual-pane audit interface for comparing original and AI-transformed content
- Image processing and storage via Alibaba Cloud OSS
- One-click publishing to multiple WordPress sites via REST API
- Version control for editorial revisions
- Asynchronous task processing for long-running operations

## Target Users

- **Editors**: Review AI-transformed content and publish to WordPress sites
- **Administrators**: Configure API keys, WordPress sites, OSS storage, and IMAP settings

## Technical Approach

The system uses asynchronous task queues (Celery) for email fetching and AI transformation, with a FastAPI backend providing REST endpoints for the audit dashboard. Content flows from email → extraction → AI transformation → editorial review → WordPress publication.
