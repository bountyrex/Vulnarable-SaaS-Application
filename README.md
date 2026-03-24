# Vulnarable-SaaS-Application
# 🏢 MultiTenantCloud CTF - Enterprise SaaS Security Challenge

[![License](https://img.shields.io/badge/License- Educational-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-red.svg)](https://flask.palletsprojects.com/)

## 📋 Overview

**MultiTenantCloud CTF** is a deliberately vulnerable multi-tenant SaaS application designed for security enthusiasts, penetration testers, and CTF players to practice real-world web application security vulnerabilities. The application simulates an enterprise cloud platform with multiple tenants, each with their own resources, users, and data.

### 🎯 Learning Objectives

- Understand and exploit **Broken Access Control** vulnerabilities (IDOR, BOLA, BPLA, BFLA)
- Master **Injection Attacks** (SQL, NoSQL, XXE, SSRF)
- Analyze and exploit **Race Conditions**
- Discover **Information Disclosure** vulnerabilities
- Learn **JWT Algorithm Confusion** attacks
- Practice **Mass Assignment** vulnerabilities
- Explore **GraphQL Introspection** and **CORS Misconfigurations**

---

## 🚀 Features

- **Multi-Tenant Architecture** - Simulates real-world SaaS platforms
- **30+ Vulnerabilities** - From easy to extreme difficulty
- **Interactive Dashboard** - Beautiful UI with sidebar navigation
- **Real-time Leaderboard** - Track your progress against other hackers
- **Flag Submission System** - Submit discovered flags for points
- **CTF Admin Panel** - Reset and manage the CTF (requires admin key)
- **Comprehensive API Documentation** - At `/api/doc`

---

## 📊 Vulnerability Categories

| Category | Vulnerabilities | Difficulty |
|----------|-----------------|------------|
| 🟣 Race Conditions | Project creation, Flag submission, Role upgrade | Extreme/Hard |
| 🟠 Broken Access Control | IDOR, BFLA, BPLA, Mass Assignment | Medium/Hard |
| 🟡 Injection Attacks | SQL, NoSQL, SSRF | Medium |
| 🟢 Information Disclosure | Secret exposure, Debug endpoints, GraphQL | Easy/Medium |
| 🔵 Auth Bypass | JWT algorithm confusion, Invite backdoor | Hard |

---

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (optional)

### Step-by-Step Installation

```bash
#LINUX
# Clone the repository
https://github.com/bountyrex/Vulnarable-SaaS-Application.git
cd multitenantcloud-ctf
# Run the application
python multitenantcloud-ctf.py

#WINDOW
Copy paste the multitenantcloud-ctf.py inside ur vscode installl the requirments and run then open localhost
```

🏆 Vulnerabilities
Category	Vulnerabilities
Race Conditions	Project creation, Flag submission, Role upgrade
Broken Access Control	IDOR, BFLA, BPLA, Mass Assignment
Injection Attacks	SQL, NoSQL, SSRF
Information Disclosure	Secret exposure, Debug endpoints, GraphQL
Auth Bypass	JWT algorithm confusion, Invite backdoor
