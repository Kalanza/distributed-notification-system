# OneSignal Push Notifications Setup Guide

## 📱 Overview

This guide will help you set up OneSignal for push notifications in your distributed notification system.

## 🚀 Quick Start

### 1. Create OneSignal Account

1. Go to [https://onesignal.com](https://onesignal.com)
2. Sign up for a free account
3. Click "New App/Website"
4. Enter your app name (e.g., "Distributed Notification System")
5. Select your platform(s):
   - **Web Push** (for web apps)
   - **iOS** (for iPhone/iPad apps)
   - **Android** (for Android apps)

### 2. Get Your API Credentials

After creating your app:

1. Go to **Settings** → **Keys & IDs**
2. Copy these values:
   - **OneSignal App ID** (e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
   - **REST API Key** (e.g., `MzQ1NjcODk5NjctYWJjZC0xMjM0LTU2Nzg5MGFiY2RlZg==`)

### 3. Configure Heroku Environment Variables

```powershell
# Set OneSignal credentials on Heroku
heroku config:set ONESIGNAL_APP_ID="your-app-id-here" --app distributed-notif-system-3037
heroku config:set ONESIGNAL_REST_API_KEY="your-rest-api-key-here" --app distributed-notif-system-3037
```

Or use the Heroku Dashboard:
1. Go to https://dashboard.heroku.com/apps/distributed-notif-system-3037/settings
2. Click "Reveal Config Vars"
3. Add:
   - **ONESIGNAL_APP_ID** = `your-app-id`
   - **ONESIGNAL_REST_API_KEY** = `your-rest-api-key`

### 4. Deploy Updated Code

The OneSignal integration is already in the code. Just deploy:

```powershell
git add .
git commit -m "Add OneSignal push notification integration"
git push heroku main
```

## 📲 Platform-Specific Setup

### Web Push Notifications

1. In OneSignal dashboard, go to **Settings** → **Web Configuration**
2. Enter your site details:
   - **Site Name**: Your app name
   - **Site URL**: `https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com`
3. Choose setup method:
   - **Typical Setup** (subdomain integration)
   - **Custom Code** (for more control)
4. Download the SDK files (if custom setup)
5. Add the initialization script to your web app

Example web integration:

```html
<script src="https://cdn.onesignal.com/sdks/OneSignalSDK.js" async=""></script>
<script>
  window.OneSignal = window.OneSignal || [];
  OneSignal.push(function() {
    OneSignal.init({
      appId: "YOUR_ONESIGNAL_APP_ID",
      notifyButton: {
        enable: true,
      },
    });
  });
</script>
```

### iOS Push Notifications

1. Need an **Apple Developer Account** ($99/year)
2. Generate **APNs Certificate** or **APNs Auth Key**
3. Upload to OneSignal:
   - Go to **Settings** → **Platforms** → **Apple iOS**
   - Upload your certificate/key
4. Integrate OneSignal iOS SDK in your app:

```swift
// In your iOS app
import OneSignal

OneSignal.initWithLaunchOptions(launchOptions, appId: "YOUR_APP_ID")
OneSignal.promptForPushNotifications(userResponse: { accepted in
  print("User accepted notifications: \(accepted)")
})
```

### Android Push Notifications

1. Need a **Firebase project** (free)
2. Get **Firebase Server Key**:
   - Go to Firebase Console → Project Settings → Cloud Messaging
   - Copy **Server Key**
3. Configure in OneSignal:
   - Go to **Settings** → **Platforms** → **Google Android**
   - Enter your Firebase Server Key
4. Integrate OneSignal Android SDK:

```java
// In your Android app (Application class)
import com.onesignal.OneSignal;

OneSignal.setLogLevel(OneSignal.LOG_LEVEL.VERBOSE, OneSignal.LOG_LEVEL.NONE);
OneSignal.initWithContext(this);
OneSignal.setAppId("YOUR_APP_ID");
```

## 🧪 Testing Push Notifications

### Option 1: Test via Heroku API

Send a push notification request:

```powershell
$headers = @{'Content-Type' = 'application/json'}
$body = @{
    notification_type = 'push'
    user_id = 'bf9a226a-db88-431d-8cdc-2dd67db08e23'
    template_code = 'welcome'
    variables = @{
        name = 'Victor'
        player_id = 'YOUR_ONESIGNAL_PLAYER_ID'  # From device
        message = 'Welcome to our app!'
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri 'https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com/api/v1/notifications/' -Method Post -Headers $headers -Body $body
```

### Option 2: Test via OneSignal Dashboard

1. Go to **Messages** → **New Push**
2. Select **Send to Test Device**
3. Add your test device's **Player ID**
4. Compose your message
5. Click **Send Message**

### Option 3: Get Player ID from Device

**Web (JavaScript):**
```javascript
OneSignal.push(function() {
  OneSignal.getUserId(function(userId) {
    console.log("OneSignal Player ID:", userId);
    // Send this to your backend
  });
});
```

**iOS (Swift):**
```swift
OneSignal.promptForPushNotifications { accepted in
  if let playerId = OneSignal.getDeviceState()?.userId {
    print("Player ID: \(playerId)")
  }
}
```

**Android (Java):**
```java
OSDeviceState device = OneSignal.getDeviceState();
if (device != null) {
    String playerId = device.getUserId();
    Log.d("OneSignal", "Player ID: " + playerId);
}
```

## 📊 User Registration Flow

### Register Device on User Creation

Update your user creation to include OneSignal player ID:

```powershell
# Create user with push notification support
$headers = @{'Content-Type' = 'application/json'}
$body = @{
    name = 'John Doe'
    email = 'john@example.com'
    password = 'SecurePass123!'
    push_token = 'ONESIGNAL_PLAYER_ID_FROM_DEVICE'
    preferences = @{
        email = $true
        push = $true
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri 'https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com/api/v1/users/' -Method Post -Headers $headers -Body $body
```

## 🔔 Advanced Features

### Segmentation

Send to specific user segments:

```python
# In your code
await onesignal_client.send_to_segments(
    segments=["Active Users", "Premium Subscribers"],
    title="Special Offer",
    message="Check out our latest features!",
    url="https://yourapp.com/offers"
)
```

### Rich Notifications

Send notifications with images and buttons:

```python
await onesignal_client.send_notification(
    player_ids=[player_id],
    title="New Photo",
    message="Check out this amazing photo!",
    image_url="https://example.com/image.jpg",
    buttons=[
        {"id": "view", "text": "View"},
        {"id": "share", "text": "Share"}
    ],
    url="https://yourapp.com/photos/123"
)
```

### Scheduled Notifications

```python
# Schedule notification for later
payload = {
    "app_id": settings.ONESIGNAL_APP_ID,
    "include_player_ids": [player_id],
    "headings": {"en": "Reminder"},
    "contents": {"en": "Don't forget!"},
    "send_after": "2025-11-14 12:00:00 GMT-0000"
}
```

## 📈 Monitoring & Analytics

### View Statistics in OneSignal Dashboard

1. Go to **Delivery** → **All Messages**
2. Click on any message to see:
   - **Sent**: Number of notifications sent
   - **Delivered**: Successfully delivered
   - **Clicked**: User engagement
   - **Converted**: Goal completions

### Track Delivery in Your System

Check notification status via Redis:

```powershell
# Get notification status
heroku redis:cli --app distributed-notif-system-3037
> GET notification:status:YOUR_NOTIFICATION_ID
```

## 🔧 Troubleshooting

### Issue: "OneSignal not configured"

**Solution**: Verify environment variables are set:
```powershell
heroku config --app distributed-notif-system-3037 | Select-String "ONESIGNAL"
```

### Issue: No player ID received

**Solution**: 
1. Verify SDK is properly initialized in your app
2. Check browser/device permissions for notifications
3. Test with OneSignal dashboard's test notification

### Issue: Notifications not received

**Checklist**:
- ✅ User has granted notification permissions
- ✅ Player ID is correctly stored in database
- ✅ OneSignal credentials are correct
- ✅ Device is not in "Do Not Disturb" mode
- ✅ Check OneSignal delivery report for errors

### Issue: Worker errors

View worker logs:
```powershell
heroku logs --tail --ps push_worker --app distributed-notif-system-3037
```

## 💡 Best Practices

### 1. Personalization
```python
variables = {
    "name": user.name,
    "message": f"Hi {user.name}, you have 3 new messages!"
}
```

### 2. Timing
- Don't send notifications during quiet hours (11 PM - 7 AM)
- Respect user timezone
- Use scheduled delivery for optimal engagement

### 3. Frequency
- Limit notifications per user (e.g., max 5/day)
- Implement frequency capping in your system
- Allow users to customize preferences

### 4. Content
- Keep titles under 40 characters
- Messages under 120 characters for best display
- Use action-oriented language
- Include relevant emojis 📱 ✨

### 5. Testing
- Always test on multiple devices/browsers
- Test different message lengths
- Verify deep links work correctly
- Check images display properly

## 📚 Resources

- **OneSignal Documentation**: https://documentation.onesignal.com/
- **REST API Reference**: https://documentation.onesignal.com/reference/
- **Web SDK Reference**: https://documentation.onesignal.com/docs/web-push-quickstart
- **iOS SDK**: https://documentation.onesignal.com/docs/ios-sdk-setup
- **Android SDK**: https://documentation.onesignal.com/docs/android-sdk-setup

## 🎯 Next Steps

1. ✅ Create OneSignal account
2. ✅ Get API credentials
3. ✅ Configure Heroku environment variables
4. ✅ Deploy updated code
5. ⏸️ Integrate SDK in your client app (web/iOS/Android)
6. ⏸️ Test notifications
7. ⏸️ Set up user segments
8. ⏸️ Configure analytics tracking

## 💰 Pricing

OneSignal has a generous **free tier**:
- ✅ Unlimited push notifications
- ✅ Unlimited devices
- ✅ Basic segmentation
- ✅ Delivery analytics

**Paid plans** start at $9/month for:
- Advanced segmentation
- Journey builder
- A/B testing
- Priority support

For most applications, the **free tier is sufficient**!

## 🚀 Quick Test Command

After setting up OneSignal credentials:

```powershell
# Test push notification (will use mock mode if OneSignal not configured)
$headers = @{'Content-Type' = 'application/json'}
$body = @{
    notification_type = 'push'
    user_id = 'test-user-123'
    template_code = 'welcome'
    variables = @{
        name = 'Test User'
        message = 'Hello from OneSignal!'
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri 'https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com/api/v1/notifications/' `
    -Method Post `
    -Headers $headers `
    -Body $body | ConvertTo-Json
```

---

**Need help?** Check the logs:
```powershell
heroku logs --tail --ps push_worker --app distributed-notif-system-3037
```
