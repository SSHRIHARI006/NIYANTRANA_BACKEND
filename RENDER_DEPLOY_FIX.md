# 🚀 Render Deployment - CRITICAL FIX REQUIRED

## ⚠️ CURRENT ISSUE
Render dashboard is running `gunicorn app:app` but your Flask app is in `server.py`, not `app.py`.

---

## 🔧 IMMEDIATE FIX (Choose Option 1 or 2)

### **Option 1: Fix Dashboard Settings (Quick Fix)**

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Select your service**: `niyantrana-backend` (or whatever you named it)
3. **Click "Settings"** (left sidebar)
4. **Scroll to "Build & Deploy"** section:
   
   - **Start Command**: Change from `gunicorn app:app` to:
     ```bash
     gunicorn server:app --bind 0.0.0.0:$PORT
     ```
   
5. **Scroll to "Environment"** section:
   
   - **Add/Update**: `PYTHON_VERSION` = `3.11.9`
   - **Add**: `CONNECTION_URL` = `your_mongodb_connection_string`
   
6. **Click "Save Changes"**

7. **Manual Deploy**:
   - Click "Manual Deploy" dropdown (top right)
   - Select **"Clear build cache & deploy"**

---

### **Option 2: Delete & Recreate from Blueprint (Recommended)**

This automatically uses your `render.yaml` configuration:

1. **Delete current service**:
   - Go to service settings
   - Scroll to bottom → "Delete Web Service"

2. **Create new service from Blueprint**:
   - Click **"New +"** → **"Blueprint"**
   - Connect to repository: `SSHRIHARI006/NIYANTRANA_BACKEND`
   - Branch: `master`
   - Render will auto-detect `render.yaml`

3. **Add Environment Variable**:
   - Before deploying, add:
     - `CONNECTION_URL` = `mongodb+srv://sambodhi:dbUserPassword@cluster0.d3x479m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0`

4. **Click "Apply"** and deploy

---

## ✅ What's Already Configured in Your Repo

- ✅ `Procfile` → Correct start command
- ✅ `render.yaml` → Complete service configuration
- ✅ `.python-version` → Forces Python 3.11.9
- ✅ `runtime.txt` → Backup Python version spec
- ✅ `requirements.txt` → Python 3.11 compatible packages
- ✅ `server.py` → Production-ready (host, PORT, debug=False)
- ✅ `.gitignore` → Excludes .env

---

## 📋 Expected Render Configuration

After fix, your service should have:

```yaml
Runtime: Python 3.11.9
Build Command: pip install -r requirements.txt
Start Command: gunicorn server:app --bind 0.0.0.0:$PORT

Environment Variables:
  - PYTHON_VERSION: 3.11.9
  - CONNECTION_URL: mongodb+srv://...
  - PORT: (auto-set by Render)
```

---

## 🔍 How to Verify It's Fixed

After redeploying, check logs for:
- ✅ `Python 3.11.9` (not 3.13)
- ✅ `gunicorn server:app` (not `app:app`)
- ✅ `Pipeline initialized successfully` (models loaded)
- ✅ `Listening at: http://0.0.0.0:XXXXX` (server running)

---

## 🐛 If Build Still Fails

### Error: "No module named 'app'"
→ Start command is wrong. Use Option 1 or 2 above.

### Error: "numpy==2.0.0rc1 not found"
→ Python 3.13 is being used. Set `PYTHON_VERSION=3.11.9` in dashboard.

### Error: "scikit-learn build failed"
→ Clear build cache and redeploy with Python 3.11.9.

---

## 📞 After Successful Deploy

Your API will be available at:
```
https://niyantrana-backend.onrender.com/api/get_trains
```

Test endpoints:
- GET `/api/get_trains`
- GET `/api/get_current_model_assignment`
- GET `/api/get_stabling_geometry`
- POST `/api/addtrain`
- POST `/api/update_status`
- GET `/api/resetstatus`

---

## 🎯 Summary

**The Problem**: Render dashboard overrides your config files  
**The Solution**: Manually fix dashboard settings OR recreate from Blueprint  
**The Result**: App runs with correct Python version and start command
