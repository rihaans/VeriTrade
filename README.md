# E-Second Hand Marketplace Management System

A Django-based e-commerce platform designed for buying and selling second-hand electronic products with built-in product evaluation and delivery management.

## Features

### User Management

- Multiple user roles:
  - Buyers
  - Sellers
  - Evaluators
  - Delivery Personnel
- User authentication and authorization
- Profile management with personal details and address information
- Credit-based transaction system

### Product Management

- Comprehensive product categorization for electronics:
  - Mobiles and Tablets
  - Laptops and Computers
  - Televisions and Monitors
  - Home Appliances
  - Computer Accessories
  - Gaming Consoles
  - Audio and Video Devices
  - And more...
- Detailed product listings with:
  - Multiple product images (up to 4)
  - Product description
  - Original purchase price and date
  - Selling price with discount options
  - Evaluation status and score

### Evaluation System

- Professional product evaluation by dedicated evaluators
- Quality scoring system
- Evaluation job management
- Historical evaluation records

### Shopping Features

- Shopping cart functionality
- Direct purchase option
- Credit-based transactions
- Product categorization and filtering

### Delivery System

- Delivery job assignment and tracking
- Delivery status updates
- Delivery personnel management
- Order tracking for buyers and sellers

## Technical Details

### Built With

- Django (Python Web Framework)
- SQLite Database
- HTML/CSS/JavaScript
- Bootstrap (Frontend Framework)

### Key Models

#### User Models

- `userFull`: Extended user profile with contact and address information
- `userCredits`: Credit management for transactions
- `evaluatorGuy`: Evaluator profile and status
- `deliveryGuy`: Delivery personnel profile and status

#### Product Models

- `product`: Complete product information and status
- `cart`: Shopping cart implementation
- `evaluatorJob`: Product evaluation assignments
- `deliveryJob`: Delivery assignments and tracking

### System Workflow

1. **Product Listing**

   - Seller uploads product with details and images
   - Product enters evaluation queue

2. **Product Evaluation**

   - Evaluator selects product from queue
   - Performs quality assessment
   - Assigns evaluation score
   - Product becomes available for purchase

3. **Purchase Process**

   - Buyer adds product to cart or makes direct purchase
   - System verifies buyer credits
   - Transaction processing
   - Delivery job creation

4. **Delivery Management**
   - Delivery personnel assignment
   - Status tracking
   - Delivery confirmation

## Installation

1. Clone the repository
2. Install required dependencies
3. Set up Django environment
4. Configure database
5. Run migrations
6. Start the development server

## Usage

### For Buyers

- Browse available products
- Add items to cart
- Make purchases using credits
- Track deliveries

### For Sellers

- List products for sale
- Track evaluation status
- Monitor sales

### For Evaluators

- Pick evaluation jobs
- Assess product quality
- Assign evaluation scores

### For Delivery Personnel

- Accept delivery assignments
- Update delivery status
- Complete deliveries

## File Structure

```
ewaste/
├── base/           # Core application features
├── delivery/       # Delivery management
├── eval/          # Evaluation system
├── events/        # Models and event handling
├── media/         # User uploads
└── templates/     # HTML templates
```

## Security Features

- User authentication
- Secure credit system
- Role-based access control
- Protected file uploads

## Database Schema

- Relational database design
- Foreign key relationships
- Unique constraints
- Transaction support

## Future Enhancements

- Payment gateway integration
- Real-time notifications
- Advanced search filters
- Review and rating system
- Mobile application
