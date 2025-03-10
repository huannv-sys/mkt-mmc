# MikroTik Manager/Monitor - Installation Guide

This document provides detailed instructions on how to install, configure, and troubleshoot the MikroTik Manager/Monitor application. It is based on the analysis of the repository at https://github.com/huannv-sys/mikrotik-manager-monitor.git.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Running the Application](#running-the-application)
5. [Troubleshooting](#troubleshooting)
6. [Known Issues](#known-issues)

## Prerequisites

Before installing the MikroTik Manager/Monitor application, ensure that you have the following prerequisites:

### System Requirements
- Operating System: Linux (recommended), Windows, or macOS
- Disk Space: At least 500MB of free space
- Memory: Minimum 2GB RAM recommended
- Network: Internet connection for downloading dependencies

### Required Software
- Git (for cloning the repository)
- Python (check version requirements in requirements.txt after cloning)
- pip (Python package manager)
- Web browser (for accessing the web interface)

### MikroTik Router Requirements
- MikroTik router with RouterOS
- API access enabled on the router
- Valid credentials with appropriate permissions
- Network connectivity between the server and the MikroTik device(s)

## Installation Steps

Follow these steps to install the MikroTik Manager/Monitor application:

### 1. Clone the Repository

First, clone the repository from GitHub:

```bash
git clone https://github.com/huannv-sys/mikrotik-manager-monitor.git
cd mikrotik-manager-monitor
