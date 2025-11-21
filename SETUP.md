# 🚨 URGENT: Security Alert & Setup Instructions

## ⚠️ Critical Security Issue Resolved

**Issue #6: Exposed API Keys** has been addressed. All hardcoded credentials have been removed from the codebase.

### Immediate Actions Required:

1. **🔄 Rotate ALL credentials** - Consider all previously committed credentials as compromised
2. **📥 Pull latest changes** - Get the updated secure configuration
3. **🔐 Set up environment variables** - Follow the setup instructions below
4. **🧹 Clean git history** - Remove secrets from repository history (see SECURITY.md)

---

## 🚀 Quick Setup

### 1. Clone & Setup Environment Variables

```bash
# Clone the repository
git clone <your-repo-url>
cd Scholar-sphere-latest

# Copy environment template
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use your preferred editor
```

### 2. Configure Your `.env` File

```env
# MySQL Configuration
MYSQL_ROOT_PASSWORD=your_strong_root_password_here
MYSQL_DATABASE=scholarsphere_db
MYSQL_USER=scholar_user
MYSQL_PASSWORD=your_strong_mysql_password_here

# Neo4j Configuration
NEO4J_PASSWORD=your_strong_neo4j_password_here

# API Keys (get these from respective platforms)
GROQ_API_KEY=your_actual_groq_api_key_here
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. Start the Application

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Access the Application

- **Frontend**: http://localhost:8080
- **Graph Service**: http://localhost:8082
- **Scrappy Service**: http://localhost:8083
- **Summary Service**: http://localhost:8085
- **Neo4j Browser**: http://localhost:7474

---

## 🔒 Security Best Practices

### ✅ Before Every Commit:

```bash
# Check what you're about to commit
git diff

# Make sure no .env files are staged
git status

# If you accidentally staged .env:
git reset HEAD .env
```

### 🛡️ Verify Your Setup:

```bash
# Ensure .env is ignored
git check-ignore .env
# Should output: .env

# Check for exposed secrets (requires truffleHog)
docker run --rm -v "$(pwd):/proj" trufflesecurity/trufflehog:latest filesystem /proj
```

---

## 📂 Project Structure

```
Scholar-sphere-latest/
├── .env                    # Your secrets (NEVER commit!)
├── .env.example           # Template for environment variables
├── .gitignore            # Prevents committing sensitive files
├── SECURITY.md           # Comprehensive security guidelines
├── cleanup-secrets.sh    # Script to clean git history
├── docker-compose.yml    # Orchestrates all services
├── Frontend-service/     # Spring Boot frontend
├── Graph-service/        # Graph data service
├── Scrappy-service/      # Data scraping service (Go)
└── Summary-service/      # AI summary service (Python)
```

---

## 🔧 Development Setup

### Running Individual Services

Each service can be run independently for development:

#### Frontend Service (Spring Boot)
```bash
cd Frontend-service
cp .env.example .env
# Edit .env with your values
./mvnw spring-boot:run
```

#### Graph Service (Spring Boot)
```bash
cd Graph-service
cp .env.example .env
# Edit .env with your values
./mvnw spring-boot:run
```

#### Scrappy Service (Go)
```bash
cd Scrappy-service
cp .env.example .env
# Edit .env with your values
export $(cat .env | xargs)
go run cmd/main.go
```

#### Summary Service (Python)
```bash
cd Summary-service
cp .env.example .env
# Edit .env with your values
pip install -r requirements.txt
python app/api.py
```

---

## 🆘 Troubleshooting

### "Error: Missing required environment variable"

**Solution**: Ensure your `.env` file exists and contains all required variables.

```bash
# Check if .env exists
ls -la .env

# Compare with example
diff .env.example .env
```

### "Database connection failed"

**Solution**: Ensure database services are running and credentials match.

```bash
# Check if services are running
docker-compose ps

# Restart services
docker-compose restart mysql neo4j
```

### "API rate limit exceeded"

**Solution**: 
- Verify your API keys are valid and active
- Check your API usage limits on respective platforms
- Consider using caching to reduce API calls

---

## 📖 Additional Documentation

- **[SECURITY.md](./SECURITY.md)** - Complete security guidelines and credential rotation instructions
- **[Frontend README](./Frontend-service/README.md)** - Frontend service documentation
- **[Scrappy README](./Scrappy-service/README.md)** - Scraping service documentation
- **[Summary README](./Summary-service/readme.md)** - Summary service documentation

---

## 🔑 Where to Get API Keys

- **GROQ API**: https://console.groq.com/keys
- **OpenAI API**: https://platform.openai.com/api-keys
- **Semantic Scholar**: https://www.semanticscholar.org/product/api

---

## 👥 Team Collaboration

### For Team Members:

If you've already cloned this repository before the security fix:

```bash
# 1. Backup your local changes
git stash

# 2. Re-clone the repository
cd ..
rm -rf Scholar-sphere-latest
git clone <your-repo-url>
cd Scholar-sphere-latest

# 3. Set up environment variables (see above)
cp .env.example .env
# Edit .env with your credentials

# 4. Restore your changes if needed
git stash pop
```

### For Repository Maintainers:

After cleaning git history:

```bash
# Force push cleaned history
git push origin --force --all
git push origin --force --tags

# Notify all team members to re-clone
```

---

## ⚖️ License

[Add your license information here]

---

## 📞 Support

For security issues, please refer to [SECURITY.md](./SECURITY.md) for reporting guidelines.

For general support, open an issue or contact the maintainers.

---

**🔒 Remember: NEVER commit your `.env` file or any file containing real credentials!**
