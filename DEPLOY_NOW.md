# Quick Heroku Deployment Instructions

Your distributed notification system is now ready to deploy to Heroku!

## What's Been Configured

✅ **Procfile** - Tells Heroku how to run your app
✅ **runtime.txt** - Specifies Python 3.11.7
✅ **requirements.txt** - All dependencies consolidated
✅ **app.json** - One-click deploy configuration
✅ **heroku.yml** - Container deployment option
✅ **Updated settings.py** - Automatic Heroku env var parsing
✅ **Deployment scripts** - Automated deployment helpers
✅ **.slugignore** - Optimize slug size

## Prerequisites Checklist

- ✅ Heroku CLI installed (Version 10.0.0 detected)
- ⬜ Heroku account created at https://heroku.com
- ⬜ Gmail App Password for SMTP (see below)
- ⬜ (Optional) OneSignal credentials for push notifications

## Getting Gmail App Password

1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to Security > 2-Step Verification > App passwords
4. Select "Mail" and generate password
5. Copy the 16-character password (no spaces)

## Deployment Options

### Option 1: Automated Script (Recommended)

```powershell
# Run the PowerShell deployment script
.\deploy-heroku.ps1 -AppName "my-notification-app" `
  -SmtpUser "your-email@gmail.com" `
  -SmtpPassword "your-16-char-app-password" `
  -SmtpFromEmail "noreply@yourdomain.com"

# With OneSignal (optional)
.\deploy-heroku.ps1 -AppName "my-notification-app" `
  -SmtpUser "your-email@gmail.com" `
  -SmtpPassword "your-app-password" `
  -SmtpFromEmail "noreply@yourdomain.com" `
  -OneSignalAppId "your-onesignal-app-id" `
  -OneSignalApiKey "your-onesignal-api-key"
```

### Option 2: Manual Deployment

```powershell
# 1. Login to Heroku
heroku login

# 2. Create app
heroku create my-notification-app

# 3. Add add-ons
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini
heroku addons:create cloudamqp:lemur

# 4. Set environment variables
heroku config:set SMTP_USER=your-email@gmail.com
heroku config:set SMTP_PASSWORD=your-app-password
heroku config:set SMTP_FROM_EMAIL=noreply@yourdomain.com
heroku config:set PYTHONPATH=/app
heroku config:set LOG_LEVEL=INFO

# 5. Deploy
git add .
git commit -m "Ready for Heroku deployment"
git push heroku main
```

### Option 3: One-Click Deploy

Click the button below to deploy instantly:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

Then set your SMTP credentials in the Heroku dashboard.

## After Deployment

### Test Your Deployment

```powershell
# Check health
Invoke-RestMethod -Uri "https://your-app-name.herokuapp.com/health"

# View API docs
Start-Process "https://your-app-name.herokuapp.com/docs"

# View logs
heroku logs --tail
```

### Send Test Notification

1. Open API docs: `https://your-app-name.herokuapp.com/docs`
2. Create a user with POST `/api/v1/users/`
3. Send notification with POST `/api/v1/notifications/`

## Common Issues & Solutions

### Issue: "App name already taken"
**Solution:** Choose a different app name or use: `heroku create` (auto-generates name)

### Issue: "Add-on already attached"
**Solution:** This is normal if re-running the script. Add-ons won't be duplicated.

### Issue: "Authentication failed"
**Solution:** Run `heroku login` and authenticate in your browser

### Issue: "SMTP authentication failed"
**Solution:** 
- Ensure 2-Step Verification is enabled on Gmail
- Use App Password, not your regular Gmail password
- Check for typos in email/password

### Issue: "Slug size too large"
**Solution:** Already configured with `.slugignore` to exclude tests and docs

## Monitoring Your App

```powershell
# View real-time logs
heroku logs --tail

# Check dyno status
heroku ps

# View app info
heroku apps:info

# Open app in browser
heroku open

# View metrics
heroku open --app your-app-name
# Click "Metrics" tab in dashboard
```

## Scaling & Performance

```powershell
# Scale web dyno (default: 1)
heroku ps:scale web=1

# Upgrade to prevent sleep (recommended for production)
heroku dyno:type web=basic

# View current scaling
heroku ps
```

## Cost Breakdown

### Free Tier (Testing)
- Dynos: Free (with sleep)
- PostgreSQL: Mini $5/month
- Redis: Mini $3/month
- CloudAMQP: Free tier
- **Total: ~$8/month**

### Production (24/7)
- Dynos: Basic $7/month (no sleep)
- PostgreSQL: Standard-0 $50/month
- Redis: Premium-0 $15/month
- CloudAMQP: Cat $19/month
- **Total: ~$91/month**

## Upgrading Services

```powershell
# Upgrade dyno to prevent sleep
heroku ps:type web=basic

# Upgrade database
heroku addons:upgrade heroku-postgresql:standard-0

# Upgrade Redis
heroku addons:upgrade heroku-redis:premium-0

# Upgrade RabbitMQ
heroku addons:upgrade cloudamqp:cat
```

## Environment Variables Reference

Required:
- `SMTP_USER` - Your Gmail email
- `SMTP_PASSWORD` - Gmail app password
- `SMTP_FROM_EMAIL` - From address for emails

Optional:
- `ONESIGNAL_APP_ID` - For push notifications
- `ONESIGNAL_REST_API_KEY` - For push notifications
- `RATE_LIMIT_PER_USER` - Default: 100
- `RATE_LIMIT_WINDOW` - Default: 60 seconds
- `LOG_LEVEL` - Default: INFO

Auto-configured by Heroku:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `CLOUDAMQP_URL` - RabbitMQ connection
- `PORT` - Web server port

## Getting Help

- **View deployment guide:** See `HEROKU_DEPLOYMENT.md` for detailed instructions
- **Check logs:** `heroku logs --tail`
- **Heroku status:** https://status.heroku.com/
- **Support:** https://help.heroku.com/

## Next Steps After Deployment

1. ✅ Test health endpoint
2. ✅ Create test user via API docs
3. ✅ Send test notification
4. ✅ Monitor logs
5. ✅ Set up custom domain (optional)
6. ✅ Configure CI/CD with GitHub Actions (optional)
7. ✅ Add monitoring with New Relic or similar (optional)

## Rollback if Needed

```powershell
# View releases
heroku releases

# Rollback to previous version
heroku rollback

# Rollback to specific version
heroku rollback v10
```

## Clean Up (Remove App)

```powershell
# WARNING: This deletes everything!
heroku apps:destroy --app your-app-name --confirm your-app-name
```

---

**Ready to deploy?** Run the deployment script or follow the manual steps above!

For questions or issues, check `HEROKU_DEPLOYMENT.md` for detailed troubleshooting.
