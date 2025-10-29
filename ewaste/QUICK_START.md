# 🚀 VeriTrade Quick Start Guide

Get VeriTrade up and running in 5 minutes!

## Prerequisites
- Python 3.13+ installed
- Git (optional)
- Command line/terminal access

## Quick Setup (Windows)

### 1. Navigate to Project Directory
```bash
cd C:\Users\rihaa\Development\Projects\VeriTrade\ewaste
```

### 2. Create Virtual Environment
```bash
python -m venv venv
```

### 3. Activate Virtual Environment
```bash
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Create Admin User (Optional)
```bash
python manage.py createsuperuser
```
Follow the prompts to create your admin account.

### 7. Run Server
```bash
python manage.py runserver
```

### 8. Access the Application
Open your browser and go to:
- **Main Site:** http://localhost:8000
- **Admin Panel:** http://localhost:8000/admin
- **Evaluator Login:** http://localhost:8000/eval/login
- **Delivery Login:** http://localhost:8000/dlv/login

## Quick Setup (Linux/Mac)

### 1. Navigate to Project Directory
```bash
cd /path/to/VeriTrade/ewaste
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
```

### 3. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Create Admin User (Optional)
```bash
python manage.py createsuperuser
```

### 7. Run Server
```bash
python manage.py runserver
```

### 8. Access Application
- **Main Site:** http://localhost:8000
- **Admin Panel:** http://localhost:8000/admin

## First Steps After Setup

### 1. Explore the Landing Page
- Visit http://localhost:8000
- Check out the new modern design!
- Browse featured products

### 2. Create a User Account
- Click "Register" in the top navigation
- Fill in your details
- Login with your credentials

### 3. As a Buyer
- Browse products by category
- Click "View Details" on any product
- Add items to your cart
- Top up credits to make purchases

### 4. As a Seller
- Go to your dashboard
- Click "Sell" to list a product
- Upload up to 4 images
- Wait for evaluation
- Track your sales

### 5. As Admin
- Visit http://localhost:8000/admin
- Login with superuser credentials
- Manage users, products, and evaluations

## Common Commands

### Start Server
```bash
python manage.py runserver
```

### Run on Different Port
```bash
python manage.py runserver 8001
```

### Create Migrations
```bash
python manage.py makemigrations
```

### Apply Migrations
```bash
python manage.py migrate
```

### Collect Static Files
```bash
python manage.py collectstatic
```

### Create Superuser
```bash
python manage.py createsuperuser
```

## Testing the New UI

### Modern Features to Check Out:
1. **Landing Page**
   - Gradient hero section
   - Feature cards with icons
   - Modern product grid
   - Professional footer

2. **Login/Signup Pages**
   - Clean, card-based design
   - Smooth animations
   - Better form styling

3. **User Dashboard**
   - Modern navigation
   - Credit display badge
   - Improved layout

4. **Responsive Design**
   - Resize your browser
   - Test on mobile devices
   - Check tablet view

## Troubleshooting

### Issue: Port already in use
**Solution:**
```bash
python manage.py runserver 8001
```

### Issue: Module not found
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: Database locked
**Solution:**
- Close the server (Ctrl+C)
- Delete `db.sqlite3`
- Run migrations again

### Issue: Static files not loading
**Solution:**
```bash
python manage.py collectstatic --clear
```

### Issue: Virtual environment not activating
**Windows:**
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## What's New? ✨

Check out these improvements:

### 🎨 Visual Upgrades
- Modern color scheme with gradients
- Professional typography
- Smooth animations and transitions
- Responsive design for all devices

### 🔒 Security Fixes
- CSRF protection enabled
- Environment variable support
- Secure secret key handling

### 📚 Documentation
- Comprehensive README
- Requirements file
- Environment configuration
- This quick start guide!

### 🔔 New Features
- Toast notification system
- Modern design system
- Improved user experience

## Development Mode

### Enable Debug Toolbar (Optional)
Add to `settings.py`:
```python
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
```

### Create Test Data
Use Django admin to:
1. Create users
2. Add products
3. Create evaluators
4. Set up delivery personnel

## Production Deployment

For production deployment:

1. **Set Environment Variables**
```bash
# Create .env file
cp .env.example .env
```

2. **Edit .env**
```env
DJANGO_SECRET_KEY=your-secure-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com
```

3. **Use Production Server**
```bash
gunicorn ewaste.wsgi:application
```

See `README.md` for detailed production setup.

## Next Steps

### Learn More
- Read [README.md](README.md) for full documentation
- Check [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) for all changes
- Explore the code structure

### Customize
- Modify colors in `veritrade-modern.css`
- Add your own logo
- Customize email templates
- Add more features

### Deploy
- Choose a hosting provider
- Set up SSL certificates
- Configure domain name
- Enable backup system

## Getting Help

### Resources
- **Documentation:** README.md
- **Changes:** IMPROVEMENTS_SUMMARY.md
- **Django Docs:** https://docs.djangoproject.com
- **Bootstrap Docs:** https://getbootstrap.com

### Common Questions

**Q: Can I change the colors?**
A: Yes! Edit CSS variables in `veritrade-modern.css`

**Q: How do I add more product categories?**
A: Edit the choices in `events/models.py`, then migrate

**Q: Can I use a real payment gateway?**
A: Yes, integrate Stripe, PayPal, or Razorpay

**Q: Is this production-ready?**
A: With proper configuration (see README.md), yes!

## Tips for Success

1. **Keep virtual environment active** when running commands
2. **Run migrations** after model changes
3. **Restart server** after settings changes
4. **Use admin panel** for testing
5. **Check browser console** for errors

## Support

Need help? Check:
- Error messages in terminal
- Browser developer console
- Django documentation
- Project documentation

---

**Happy coding! 🎉**

*VeriTrade - Your modern e-waste marketplace platform*
