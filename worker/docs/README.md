# Participant Service Agent Documentation

## Overview

This directory contains documentation for the Participant Service Agent.

## Contents

- [Architecture Overview](architecture.md) - High-level architecture of the system
- [Setup Guide](setup.md) - Setup and installation instructions
- [API Documentation](api/) - Documentation for service APIs
- [Development Guide](development.md) - Guidelines for development

## Project Structure

```
worker/
├── agent.py - Main entry point for the agent
├── config.py - Configuration management
├── services/ - Service modules for external integrations
├── models/ - Data models
├── schemas/ - Type definitions and schemas
├── managers/ - Coordinator modules
├── plugins/ - Plugin modules for external capabilities
├── utils/ - Utility modules
│   └── logger.py - Logging configuration
├── docs/ - Documentation
└── tests/ - Test suite
    ├── unit/ - Unit tests
    ├── integration/ - Integration tests
    └── e2e/ - End-to-end tests
```
