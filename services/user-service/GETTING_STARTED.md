# ✅ User Service - Team Onboarding Checklist

## 🎯 Before You Start

- [ ] Docker Desktop installed and running
- [ ] Git installed
- [ ] PowerShell (comes with Windows)
- [ ] Text editor/IDE (VS Code recommended)
- [ ] Basic understanding of REST APIs
- [ ] Familiarity with Python (helpful but not required)

## 📚 Step 1: Read Documentation (15 minutes)

- [ ] Read `README.md` - Understand the service overview
- [ ] Skim `PROJECT_SUMMARY.md` - See what's been built
- [ ] Review `QUICK_REFERENCE.md` - Learn common commands
- [ ] Check `API_EXAMPLES.md` - See example API calls

## 🚀 Step 2: Get It Running (10 minutes)

```powershell
# Open PowerShell in user-service directory
cd c:\Users\USER\Desktop\dns-core\services\user-service

# Run the quick start script
.\start.ps1

# Follow the prompts - it will:
# ✓ Create .env file
# ✓ Start Docker containers
# ✓ Run database migrations
# ✓ Optionally create a superuser
```

**Expected Output**: You should see "✅ User Service is ready!"

## 🔍 Step 3: Verify Installation (5 minutes)

Open these URLs in your browser:

- [ ] http://localhost:8000/swagger/ - Should show API documentation
- [ ] http://localhost:8000/api/v1/health/ - Should return healthy status
- [ ] http://localhost:8000/admin/ - Should show Django admin login
- [ ] http://localhost:15672/ - RabbitMQ management (guest/guest)

If all load successfully, you're good to go! ✅

## 🧪 Step 4: Test the API (10 minutes)

### Option A: Use Swagger UI (Easiest)
1. Go to http://localhost:8000/swagger/
2. Find "POST /api/v1/users/" endpoint
3. Click "Try it out"
4. Use this example data:
```json
{
  "name": "Test User",
  "email": "test@example.com",
  "password": "TestPass123!",
  "preferences": {
    "email": true,
    "push": true
  }
}
```
5. Click "Execute"
6. You should get a 201 response with user data and tokens

### Option B: Use PowerShell
```powershell
# Copy the examples from API_EXAMPLES.md
# Or run this simple test:
$body = @{
    name = "Test User"
    email = "test@example.com"
    password = "TestPass123!"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users/" -Method POST -Body $body -ContentType "application/json"
```

- [ ] Successfully registered a user
- [ ] Received access and refresh tokens
- [ ] Can see user in Django admin (if you created superuser)

## 📖 Step 5: Understand the Code (20 minutes)

Read these files in order:

1. **`users/models.py`** - Understand the User model
   - [ ] User fields (email, name, push_token)
   - [ ] UserPreference fields (email, push)
   - [ ] IdempotencyKey for request deduplication

2. **`users/serializers.py`** - See how data is validated
   - [ ] UserRegistrationSerializer
   - [ ] LoginSerializer
   - [ ] UserSerializer

3. **`users/views.py`** - Study the API endpoints
   - [ ] UserRegistrationView - How registration works
   - [ ] LoginView - How authentication works
   - [ ] UserProfileView - CRUD operations

4. **`users/rabbitmq_consumer.py`** - Message queue integration
   - [ ] How it connects to RabbitMQ
   - [ ] Message processing logic
   - [ ] Circuit breaker implementation

## 🛠️ Step 6: Common Tasks (Practice)

### View Logs
```powershell
docker-compose logs -f user_service
```
- [ ] Can view real-time logs

### Access Django Shell
```powershell
docker-compose exec user_service python manage.py shell
```
```python
from users.models import User
User.objects.count()  # Should show number of users
```
- [ ] Can interact with database via shell

### Run Tests
```powershell
docker-compose exec user_service pytest
```
- [ ] All tests pass

### Stop Services
```powershell
docker-compose down
```
- [ ] Services stopped successfully

### Restart Services
```powershell
docker-compose up -d
```
- [ ] Services restarted successfully

## 📝 Step 7: Make Your First Change (Optional)

Try adding a new field to the User model:

1. **Edit `users/models.py`**
```python
# Add this field to User model
phone_number = models.CharField(max_length=20, blank=True, null=True)
```

2. **Create migration**
```powershell
docker-compose exec user_service python manage.py makemigrations
```

3. **Apply migration**
```powershell
docker-compose exec user_service python manage.py migrate
```

4. **Update serializer** (users/serializers.py)
```python
# Add 'phone_number' to fields list in UserSerializer
```

5. **Test it** - Register a new user with phone_number

- [ ] Successfully added and tested a new field

## 🤝 Step 8: Team Coordination

### Understand Your Role
- [ ] You're responsible for the **User Service**
- [ ] Other services will call your API for user data
- [ ] You consume from `push.queue` for notifications

### Integration Points
- [ ] **API Gateway** - Will route requests to you
- [ ] **Email Service** - Needs user email preferences
- [ ] **Push Service** - Needs user push preferences
- [ ] **Template Service** - May need user data

### Communication
- [ ] Understand the message format you consume
- [ ] Know what data other services need from you
- [ ] Document any API changes you make

## 🐛 Troubleshooting

### Services Won't Start
```powershell
# Check if ports are already in use
netstat -ano | findstr "8000"
netstat -ano | findstr "5432"

# Kill process if needed
taskkill /PID <process_id> /F

# Try again
docker-compose down -v
docker-compose up -d
```

### Database Connection Error
```powershell
# Reset everything
docker-compose down -v
docker-compose up -d
# Wait 10 seconds
docker-compose exec user_service python manage.py migrate
```

### Can't Access Swagger
- Check if service is running: `docker-compose ps`
- Check logs: `docker-compose logs user_service`
- Verify URL: http://localhost:8000/swagger/

### Tests Failing
```powershell
# Make sure database is ready
docker-compose exec user_service python manage.py migrate

# Run tests again
docker-compose exec user_service pytest -v
```

## 📞 Getting Help

1. **Check Documentation**
   - README.md for features
   - QUICK_REFERENCE.md for commands
   - API_EXAMPLES.md for API usage

2. **Check Logs**
   ```powershell
   docker-compose logs -f user_service
   ```

3. **Ask Your Team**
   - Share what you tried
   - Include error messages
   - Show relevant logs

4. **Check System Diagram**
   - Review the architecture diagram in the task description
   - Understand how your service fits in

## ✅ Completion Checklist

### Basic Understanding
- [ ] I can explain what the user service does
- [ ] I can describe the main API endpoints
- [ ] I understand the authentication flow
- [ ] I know how RabbitMQ integration works

### Technical Skills
- [ ] I can start and stop the service
- [ ] I can read and understand the logs
- [ ] I can test endpoints using Swagger
- [ ] I can run the test suite
- [ ] I can access the database

### Team Readiness
- [ ] I know my service's responsibilities
- [ ] I understand integration points
- [ ] I can explain our API to other teams
- [ ] I'm ready to answer questions in the presentation

## 🎓 Next Steps

Once you've completed this checklist:

1. **Explore Advanced Features**
   - Study the circuit breaker pattern
   - Understand idempotency implementation
   - Learn about correlation IDs

2. **Customize for Your Needs**
   - Add any team-specific features
   - Adjust configuration as needed
   - Enhance documentation

3. **Prepare for Integration**
   - Test with other team's services
   - Verify message queue communication
   - Check API contracts

4. **Prepare Presentation**
   - Screenshots of working service
   - Demo of key features
   - Explanation of architecture decisions

## 🏆 You're Ready!

Congratulations! You now understand:
- ✅ How the user service works
- ✅ How to run and test it
- ✅ How to make changes
- ✅ How it integrates with other services

**Good luck with your internship project! 🚀**

---

**Questions?** Check the documentation files or ask your team!
