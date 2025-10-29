# VeriTrade - E-Waste Marketplace Platform

A modern, secure marketplace for buying and selling pre-owned electronics with built-in quality assurance through professional evaluation.

## Features

### Core Functionality
- **Multi-Role System**: Buyers/Sellers, Evaluators, Delivery Personnel, and Admins
- **Quality Assurance**: Professional product evaluation before listing
- **Secure Transactions**: Credit-based payment system
- **Delivery Management**: Integrated delivery tracking with geolocation
- **15 Product Categories**: Mobiles, Laptops, TVs, Gaming Consoles, and more

### Recent UI/UX Improvements ✨
- Modern, responsive design with custom CSS framework
- Gradient hero sections and card-based layouts
- Improved navigation with modern header
- Enhanced authentication pages (login/signup)
- Better product cards with hover effects
- Professional color scheme and typography
- Toast notification system ready
- Mobile-responsive design

### Security Enhancements 🔒
- CSRF protection re-enabled
- Environment variable support for sensitive settings
- Secure SECRET_KEY handling
- Production-ready configuration options

## Tech Stack

**Backend:**
- Django 5.1
- Python 3.13
- SQLite (development)
- Django ORM

**Frontend:**
- HTML5/CSS3/JavaScript
- Bootstrap 4
- Custom Modern CSS Framework
- Font Awesome Icons
- jQuery

**Additional Libraries:**
- geopy (geocoding)
- Pillow (image handling)

## Installation

### Prerequisites
- Python 3.13+
- pip
- virtualenv (recommended)

### Setup Instructions

1. **Clone the repository**
```bash
git clone <repository-url>
cd VeriTrade/ewaste
```

2. **Create and activate virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set your secret key and other settings
# IMPORTANT: Generate a new SECRET_KEY for production!
```

5. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create a superuser (admin)**
```bash
python manage.py createsuperuser
```

7. **Collect static files**
```bash
python manage.py collectstatic
```

8. **Run the development server**
```bash
python manage.py runserver
```

9. **Access the application**
- Main site: http://localhost:8000
- Admin panel: http://localhost:8000/admin
- Evaluator portal: http://localhost:8000/eval/login
- Delivery portal: http://localhost:8000/dlv/login

## Project Structure

```
ewaste/
├── ewaste/                 # Main project configuration
│   ├── settings.py        # Django settings (improved security)
│   ├── urls.py            # URL routing
│   ├── wsgi.py           # WSGI config
│   └── asgi.py           # ASGI config
├── events/                # Core models app
│   ├── models.py         # All database models
│   ├── static/           # Static files
│   │   └── assets/
│   │       └── css/
│   │           └── veritrade-modern.css  # New modern CSS
│   └── admin.py          # Admin configuration
├── base/                  # Buyer/Seller app
│   ├── views.py          # User views
│   └── urls.py           # Base routing
├── eval/                  # Evaluator app
│   ├── views.py          # Evaluation views
│   └── urls.py           # Eval routing
├── delivery/              # Delivery personnel app
│   ├── views.py          # Delivery views
│   └── urls.py           # Delivery routing
├── templates/             # HTML templates
│   ├── index.html        # Landing page (redesigned)
│   ├── base/             # User templates (improved)
│   ├── eval/             # Evaluator templates
│   └── delivery/         # Delivery templates
├── media/                 # User uploads
├── db.sqlite3            # SQLite database
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## User Workflows

### For Buyers
1. Register and create an account
2. Browse products by category
3. View detailed product information
4. Add items to cart
5. Purchase using credits
6. Track delivery status

### For Sellers
1. Register and create account
2. List products with images and details
3. Products enter evaluation queue
4. Once evaluated, products become available
5. Track sales and deliveries
6. Receive credits upon sale

### For Evaluators
1. Register as evaluator
2. View available products for evaluation
3. Select and evaluate products
4. Assign quality scores
5. Track evaluation history

### For Delivery Personnel
1. Register as delivery person
2. View available delivery jobs
3. Accept delivery assignments
4. View seller/buyer locations (with geocoding)
5. Update delivery status

## Key Features Explained

### Credit System
- Virtual currency for transactions
- Users can top up credits
- Secure payment flow
- Credit balance tracking

### Product Evaluation
- All products must be evaluated before sale
- Professional quality assessment
- Evaluation score visible to buyers
- One job per evaluator at a time

### Delivery Management
- Automatic delivery job creation on purchase
- Geolocation support for addresses
- Real-time status tracking
- Delivery history

## Configuration

### Environment Variables
Create a `.env` file based on `.env.example`:

```env
DJANGO_SECRET_KEY=your-very-secure-secret-key
DJANGO_DEBUG=True  # Set to False in production
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
```

### Production Deployment

Before deploying to production:

1. **Security Settings**
   - Set `DEBUG=False`
   - Configure `ALLOWED_HOSTS` properly
   - Use strong `SECRET_KEY`
   - Enable HTTPS
   - Configure proper database (PostgreSQL/MySQL)

2. **Static Files**
   - Configure whitenoise or use a CDN
   - Run `collectstatic`

3. **Database**
   - Migrate from SQLite to PostgreSQL/MySQL
   - Configure database backups

4. **Server**
   - Use gunicorn or uwsgi
   - Configure nginx/apache
   - Set up SSL certificates

## Development

### Adding New Features
1. Create models in `events/models.py`
2. Run migrations
3. Create views in respective app
4. Update templates
5. Add URLs

### Styling Guidelines
- Use CSS variables from `veritrade-modern.css`
- Follow existing design patterns
- Maintain responsive design
- Test on multiple devices

### Code Style
- Follow PEP 8 for Python
- Use meaningful variable names
- Comment complex logic
- Keep functions focused and small

## Troubleshooting

### Common Issues

**Database errors after changes:**
```bash
python manage.py makemigrations
python manage.py migrate
```

**Static files not loading:**
```bash
python manage.py collectstatic --clear
```

**Port already in use:**
```bash
python manage.py runserver 8001
```

**Import errors:**
```bash
pip install -r requirements.txt
```

## Security Considerations

### Important Security Notes
- CSRF protection is now enabled (previously disabled)
- Change SECRET_KEY before production
- Use environment variables for sensitive data
- Set DEBUG=False in production
- Configure proper ALLOWED_HOSTS
- Use HTTPS in production
- Regularly update dependencies
- Implement rate limiting for production
- Add proper authentication rate limiting

## Future Enhancements

- [ ] Real payment gateway integration
- [ ] Email notifications
- [ ] Advanced search and filtering
- [ ] Product reviews and ratings
- [ ] Wishlist functionality
- [ ] Real-time chat support
- [ ] Mobile app (React Native/Flutter)
- [ ] AI-powered product recommendations
- [ ] Enhanced analytics dashboard
- [ ] Multiple currency support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational purposes.

## Support

For issues and questions:
- Check the documentation
- Review existing issues
- Create a new issue with details

## Acknowledgments

- Django community
- Bootstrap team
- Font Awesome
- All contributors

---

**Built with ❤️ for a sustainable future**

*VeriTrade - Reducing E-Waste, One Transaction at a Time*
