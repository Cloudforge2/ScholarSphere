# 🔒 Security Guidelines for ScholarSphere

## ⚠️ CRITICAL: Exposed Secrets Issue

**This repository previously contained exposed API keys and passwords.** This security issue has been addressed by:
1. Removing hardcoded credentials from configuration files
2. Implementing environment variable-based configuration
3. Adding comprehensive `.gitignore` rules

## 🚨 Immediate Actions Required

### 1. **Rotate All Exposed Credentials**

All passwords and API keys that were previously committed to the repository should be considered compromised and **MUST BE ROTATED IMMEDIATELY**:

- ✅ **MySQL Password**: Change from `StrongPassword123!` to a new strong password
- ✅ **Neo4j Password**: Change from `test123!` to a new strong password
- ✅ **GROQ API Key**: Regenerate your GROQ API key at [Groq Console](https://console.groq.com/)
- ✅ **OpenAI API Key**: Regenerate your OpenAI API key at [OpenAI Platform](https://platform.openai.com/api-keys)

### 2. **Remove Secrets from Git History**

Run these commands to remove secrets from your git history:

```bash
# Install git-filter-repo (recommended method)
pip install git-filter-repo

# Backup your repository first!
cd /home/kunal/ScholarSphere/Scholar-sphere-latest
git clone . ../Scholar-sphere-backup

# Remove sensitive data from history
git filter-repo --path Frontend-service/src/main/resources/application.properties --invert-paths
git filter-repo --path Graph-service/src/main/resources/application.yml --invert-paths

# Or use BFG Repo-Cleaner (alternative)
# Download from: https://rtyley.github.io/bfg-repo-cleaner/
# java -jar bfg.jar --replace-text passwords.txt
```

**⚠️ WARNING**: This will rewrite git history. All team members will need to re-clone the repository.

### 3. **Force Push Changes**

```bash
git push origin --force --all
git push origin --force --tags
```

## 📋 Setup Instructions

### Prerequisites

1. **Create a `.env` file** in the root directory by copying `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. **Fill in your actual secrets** in the `.env` file:
   ```env
   # MySQL Configuration
   MYSQL_ROOT_PASSWORD=your_strong_root_password_here
   MYSQL_DATABASE=scholarsphere_db
   MYSQL_USER=scholar_user
   MYSQL_PASSWORD=your_strong_mysql_password_here

   # Neo4j Configuration
   NEO4J_PASSWORD=your_strong_neo4j_password_here

   # API Keys
   GROQ_API_KEY=your_actual_groq_api_key_here
   OPENAI_API_KEY=your_actual_openai_api_key_here
   ```

3. **NEVER commit the `.env` file** to git. It's already in `.gitignore`.

### For Individual Services

Each service also has its own `.env.example` file. If running services individually:

```bash
# Frontend Service
cd Frontend-service
cp .env.example .env
# Edit .env with your values

# Graph Service
cd Graph-service
cp .env.example .env
# Edit .env with your values

# Scrappy Service
cd Scrappy-service
cp .env.example .env
# Edit .env with your values

# Summary Service
cd Summary-service
cp .env.example .env
# Edit .env with your values
```

## 🐳 Running with Docker Compose

After setting up your `.env` file in the root directory:

```bash
# Docker Compose will automatically load variables from .env
docker-compose up -d
```

## 🔐 Best Practices

### ✅ DO:
- Store all secrets in environment variables
- Use `.env` files for local development (never commit them)
- Use secret management services in production (AWS Secrets Manager, Azure Key Vault, etc.)
- Rotate credentials regularly
- Use strong, unique passwords for each service
- Review `.gitignore` before committing
- Use `git diff` before committing to check for sensitive data
- Enable GitHub secret scanning

### ❌ DON'T:
- Never hardcode passwords or API keys in source code
- Never commit `.env` files
- Never commit files with real credentials
- Never share API keys in chat, email, or tickets
- Don't use default or weak passwords
- Don't reuse passwords across services

## 🛡️ GitHub Security Features

Enable these features in your GitHub repository:

1. **Secret Scanning**: Settings → Code security and analysis → Secret scanning
2. **Dependabot Alerts**: Settings → Code security and analysis → Dependabot alerts
3. **Code Scanning**: Settings → Code security and analysis → Code scanning

## 📞 Reporting Security Issues

If you discover a security vulnerability, please:
1. **Do NOT** open a public GitHub issue
2. Contact the repository maintainers directly
3. Wait for confirmation before disclosing publicly

## 🔄 Credential Rotation Schedule

- **Development**: Rotate every 90 days
- **Production**: Rotate every 30 days
- **Compromised**: Rotate immediately

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [Docker Secrets Management](https://docs.docker.com/engine/swarm/secrets/)
- [12 Factor App - Config](https://12factor.net/config)

---

**Last Updated**: November 21, 2025
**Status**: ✅ Security measures implemented - Credential rotation required
