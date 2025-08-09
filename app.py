from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import bcrypt
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sikhne_ke_liye_secret_key'

# --- Login Manager Setup ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# --- In-Memory Database (Python Dictionaries and Lists) ---
USERS = {}
FOODS = {
    1: {'id': 1, 'name': 'Butter Paneer', 'description': 'Creamy and rich paneer dish.', 'price': 250.00, 'image_file': 'img1.jpg'},
    2: {'id': 2, 'name': 'Masala Dosa', 'description': 'Crispy dosa with potato filling.', 'price': 150.00, 'image_file': 'img2.jpg'},
    3: {'id': 3, 'name': 'Chole Bhature', 'description': 'Spicy chickpeas with fried bread.', 'price': 180.00, 'image_file': 'img3.jpg'},
    4: {'id': 4, 'name': 'Veg Biryani', 'description': 'Aromatic rice with mixed vegetables.', 'price': 220.00, 'image_file': 'img4.jpg'},
    5: {'id': 5, 'name': 'Pav Bhaji', 'description': 'Spicy mashed vegetables with soft bread.', 'price': 160.00, 'image_file': 'img5.jpg'},
    6: {'id': 6, 'name': 'Veg Thali', 'description': 'A complete meal with various dishes.', 'price': 300.00, 'image_file': 'img6.jpg'}
}
CARTS = {} 
ORDERS = [] 

# Admin User
admin_pass = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())
USERS['admin@example.com'] = {'name': 'Admin', 'password': admin_pass, 'is_admin': True, 'id': 1}
next_user_id = 2

class User(UserMixin):
    def __init__(self, id, name, email, is_admin=False):
        self.id = id
        self.name = name
        self.email = email
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    for email, user_data in USERS.items():
        if str(user_data.get('id')) == str(user_id):
            return User(id=user_data['id'], name=user_data['name'], email=email, is_admin=user_data['is_admin'])
    return None

@app.context_processor
def inject_cart_count():
    if not current_user.is_authenticated:
        return dict(cart_count=0)
    user_cart = CARTS.get(current_user.id, {})
    count = sum(user_cart.values())
    return dict(cart_count=count)

@app.route('/')
def home():
    return render_template('home.html', foods=list(FOODS.values()))

@app.route('/register', methods=['GET', 'POST'])
def register():
    global next_user_id
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        if email in USERS:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
        USERS[email] = {'name': name, 'password': hashed_password, 'is_admin': False, 'id': next_user_id}
        next_user_id += 1
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        user_data = USERS.get(email)
        if user_data and bcrypt.checkpw(password, user_data['password']):
            user_obj = User(id=user_data['id'], name=user_data['name'], email=email, is_admin=user_data['is_admin'])
            login_user(user_obj)
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:food_id>')
@login_required
def add_to_cart(food_id):
    user_id = current_user.id
    if user_id not in CARTS:
        CARTS[user_id] = {}
    CARTS[user_id][food_id] = CARTS[user_id].get(food_id, 0) + 1
    flash('Item added to cart!', 'success')
    return redirect(url_for('home'))

@app.route('/cart')
@login_required
def cart():
    user_cart_ids = CARTS.get(current_user.id, {})
    cart_items = []
    total_price = 0
    for food_id, quantity in user_cart_ids.items():
        food_item = FOODS.get(food_id)
        if food_item:
            total_price += food_item['price'] * quantity
            # Yahan hum poora food_item dictionary bhej rahe hain, jismein 'id' key hai.
            cart_items.append({**food_item, 'quantity': quantity})
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/remove_from_cart/<int:food_id>', methods=['POST'])
@login_required
def remove_from_cart(food_id):
    user_id = current_user.id
    if user_id in CARTS and food_id in CARTS[user_id]:
        del CARTS[user_id][food_id]
        flash("Item removed from cart.", "success")
    return redirect(url_for('cart'))

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    user_id = current_user.id
    user_cart = CARTS.get(user_id, {})
    if not user_cart:
        flash("Your cart is empty.", "danger")
        return redirect(url_for('cart'))
    total_price = sum(FOODS[food_id]['price'] * quantity for food_id, quantity in user_cart.items())
    new_order = {'id': len(ORDERS) + 1, 'user_id': user_id, 'total_price': total_price, 'status': 'Order Placed', 'order_date': datetime.now()}
    ORDERS.append(new_order)
    CARTS[user_id] = {}
    flash("Order placed successfully!", "success")
    return redirect(url_for('my_orders'))

@app.route('/my_orders')
@login_required
def my_orders():
    user_orders = [order for order in ORDERS if order['user_id'] == current_user.id]
    return render_template('my_orders.html', orders=sorted(user_orders, key=lambda x: x['order_date'], reverse=True))

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        return redirect(url_for('home'))
    
    orders_with_details = []
    for order in ORDERS:
        user_email = next((email for email, data in USERS.items() if data['id'] == order['user_id']), None)
        user_name = USERS.get(user_email, {}).get('name', 'N/A')
        orders_with_details.append({**order, 'name': user_name, 'email': user_email})

    return render_template('admin_orders.html', orders=sorted(orders_with_details, key=lambda x: x['order_date'], reverse=True))

@app.route('/admin/order/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        return redirect(url_for('home'))
    status = request.form['status']
    for order in ORDERS:
        if order['id'] == order_id:
            order['status'] = status
            break
    return redirect(url_for('admin_orders'))

if __name__ == '__main__':
    app.run(debug=True)